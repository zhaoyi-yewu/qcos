/*
 * ----------------------------------------------------------------------
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *          http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *      WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include "compiler/qasm_compiler/parser/scanner.hpp"

#include <cstdint>
#include <istream>
#include <optional>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>

namespace qasm {
std::optional<Token> Scanner::consumeWhitespaceAndComments() {
  while (isSpace(ch)) {
    nextCh();
  }
  if (ch == '/' && peek() == '/') {
    Token t(line, col);
    // Zero-copy: record start position and advance through comment content,
    // then create a string_view into the buffer_.
    const char* contentStart = ptr_ - 1;
    while (ch != '\n' && ch != 0) {
      nextCh();
    }
    size_t contentLen = static_cast<size_t>(ptr_ - 1 - contentStart);
    if (ch == '\n') {
      nextCh();
    }

    // Fast prefix check to avoid expensive regex on every comment line.
    // InitialLayout / OutputPermutation comments are extremely rare
    // (0-2 per file), but this code runs for every single-line comment.
    bool isLayout = false;
    bool isPerm = false;
    if (contentLen >= 2 && contentStart[0] == 'i' && contentStart[1] == ' ') {
      // regex_search requires a std::string for the subject, but this path
      // is extremely rare so the allocation is acceptable.
      std::string content(contentStart, contentLen);
      static const auto INITIAL_LAYOUT_REGEX = std::regex("i (\\d+ )*(\\d+)");
      isLayout = std::regex_search(content, INITIAL_LAYOUT_REGEX);
    } else if (contentLen >= 2 && contentStart[0] == 'o' && contentStart[1] == ' ') {
      std::string content(contentStart, contentLen);
      static const auto OUTPUT_PERMUTATION_REGEX =
          std::regex("o (\\d+ )*(\\d+)");
      isPerm = std::regex_search(content, OUTPUT_PERMUTATION_REGEX);
    }

    if (isLayout) {
      t.kind = Token::Kind::InitialLayout;
    } else if (isPerm) {
      t.kind = Token::Kind::OutputPermutation;
    } else {
      return consumeWhitespaceAndComments();
    }

    t.str = std::string_view(contentStart, contentLen);
    t.endCol = col;
    t.endLine = line;
    return t;
  }
  if (ch == '/' && peek() == '*') {
    // consume /*
    nextCh();
    nextCh();
    while (ch != 0 && (ch != '*' || peek() != '/')) {
      nextCh();
    }
    // consume */
    expect('*');
    expect('/');

    // tail calls should be optimized away
    return consumeWhitespaceAndComments();
  }

  return {};
}

Token Scanner::consumeName() {
  Token t(line, col);

  // Zero-copy: record start position and advance through identifier chars,
  // then create a string_view into the buffer_ — no std::string allocation.
  const char* start = ptr_ - 1;  // ptr_ already advanced past first char by nextCh()
  while (isFirstIdChar(ch) || isNum(ch)) {
    nextCh();
  }
  t.str = std::string_view(start, static_cast<size_t>(ptr_ - start - 1));

  auto it = keywords->find(t.str);
  t.kind = (it != keywords->end()) ? it->second : Token::Kind::Identifier;

  t.endCol = col;
  t.endLine = line;
  return t;
}

bool Scanner::isValidDigit(const uint8_t base, const char c) {
  if (base == 2) {
    return c == '0' || c == '1';
  }
  if (base == 8) {
    return c >= '0' && c <= '7';
  }
  if (base == 10) {
    return isNum(c);
  }
  if (base == 16) {
    return isHex(c);
  }
  return false;
}

std::string Scanner::consumeNumberLiteral(const uint8_t base) {
  std::string ss;
  ss.reserve(32);

  while (isValidDigit(base, ch) || ch == '_') {
    if (ch != '_') {
      ss.push_back(ch);
    }
    nextCh();
  }

  return ss;
}

uint64_t Scanner::parseIntegerLiteral(const std::string& str,
                                      const uint8_t base) {
  uint64_t val = 0;
  for (const auto c : str) {
    if (isNum(c)) {
      val *= base;
      val += static_cast<uint64_t>(c) - '0';
    } else {
      val *= base;
      val += static_cast<uint64_t>(c) - 'a' + 10;
    }
  }
  return val;
}

Token Scanner::consumeNumberLiteral() {
  Token t(line, col);
  uint8_t base = 10;

  if (ch == '0') {
    switch (peek()) {
      case 'b':
      case 'B':
        base = 2;
        nextCh();
        nextCh();
        break;
      case 'o':
        base = 8;
        nextCh();
        nextCh();
        break;
      case 'x':
      case 'X':
        base = 16;
        nextCh();
        nextCh();
        break;
      default:
        break;
    }
  }
  bool negative = false;
  if (ch == '-') {
    if (base != 10) {
      error("Negative numbers are only allowed in base 10");
    }
    negative = true;
    nextCh();
  }

  const auto valBeforeDecimalSeparator = consumeNumberLiteral(base);

  if (ch == '.' || ch == 'e' || ch == 'E') {
    if (base != 10) {
      error("Float literals are only allowed in base 10");
    }

    std::string ss;
    ss.reserve(valBeforeDecimalSeparator.size() + 32);
    ss += valBeforeDecimalSeparator;

    if (ch == '.') {
      ss += ch;
      nextCh();
      const auto valAfterDecimalSeparator = consumeNumberLiteral(base);
      ss += valAfterDecimalSeparator;
    }

    if (ch == 'e' || ch == 'E') {
      ss += ch;
      nextCh();
      if (ch == '+' || ch == '-') {
        ss += ch;
        nextCh();
      }
      const auto valAfterExponent = consumeNumberLiteral(base);
      ss += valAfterExponent;
    }

    try {
      t.valReal = std::stod(ss);
    } catch (std::invalid_argument&) {
      error("Unable to parse float literal");
    }

    t.kind = Token::Kind::FloatLiteral;
    if (negative) {
      t.valReal *= -1;
    }

    return t;
  }

  t.val = static_cast<int64_t>(
      parseIntegerLiteral(valBeforeDecimalSeparator, base));
  t.kind = Token::Kind::IntegerLiteral;
  if (negative) {
    t.val *= -1;
    t.isSigned = true;
  }

  t.endCol = col;
  t.endLine = line;

  return t;
}

Token Scanner::consumeHardwareQubit() {
  Token t(line, col);

  expect('$');

  t.kind = Token::Kind::HardwareQubit;
  t.val = 0;
  while (isNum(ch)) {
    t.val *= 10;
    t.val += static_cast<int64_t>(ch - '0');
    nextCh();
  }

  t.endCol = col;
  t.endLine = line;

  return t;
}

Token Scanner::consumeString() {
  Token t(line, col);
  t.kind = Token::Kind::StringLiteral;

  if (ch != '"' && ch != '\'') {
    error("expected `\"` or `'`");
    t.kind = Token::Kind::None;
    return t;
  }
  const auto delim = ch;
  nextCh();

  // Zero-copy: record start position and advance through string content,
  // then create a string_view into the buffer_ — no std::string allocation.
  const char* start = ptr_ - 1;
  while (ch != delim) {
    nextCh();
  }

  t.str = std::string_view(start, static_cast<size_t>(ptr_ - start - 1));

  expect(delim);

  t.endCol = col;
  t.endLine = line;

  return t;
}

const std::unordered_map<std::string_view, Token::Kind> Scanner::s_keywords = {
    {"OPENQASM", Token::Kind::OpenQasm},
    {"include", Token::Kind::Include},
    {"defcalgrammar", Token::Kind::DefCalGrammar},
    {"def", Token::Kind::Def},
    {"cal", Token::Kind::Cal},
    {"defcal", Token::Kind::DefCal},
    {"gate", Token::Kind::Gate},
    {"opaque", Token::Kind::Opaque},
    {"extern", Token::Kind::Extern},
    {"box", Token::Kind::Box},
    {"let", Token::Kind::Let},
    {"break", Token::Kind::Break},
    {"continue", Token::Kind::Continue},
    {"if", Token::Kind::If},
    {"else", Token::Kind::Else},
    {"end", Token::Kind::End},
    {"return", Token::Kind::Return},
    {"for", Token::Kind::For},
    {"while", Token::Kind::While},
    {"in", Token::Kind::In},
    {"pragma", Token::Kind::Pragma},
    {"input", Token::Kind::Input},
    {"output", Token::Kind::Output},
    {"const", Token::Kind::Const},
    {"readonly", Token::Kind::ReadOnly},
    {"mutable", Token::Kind::Mutable},
    {"qreg", Token::Kind::Qreg},
    {"qubit", Token::Kind::QBit},
    {"creg", Token::Kind::CReg},
    {"bool", Token::Kind::Bool},
    {"bit", Token::Kind::Bit},
    {"int", Token::Kind::Int},
    {"uint", Token::Kind::Uint},
    {"float", Token::Kind::Float},
    {"angle", Token::Kind::Angle},
    {"complex", Token::Kind::Complex},
    {"array", Token::Kind::Array},
    {"void", Token::Kind::Void},
    {"duration", Token::Kind::Duration},
    {"stretch", Token::Kind::Stretch},
    {"gphase", Token::Kind::Gphase},
    {"inv", Token::Kind::Inv},
    {"pow", Token::Kind::Pow},
    {"ctrl", Token::Kind::Ctrl},
    {"negctrl", Token::Kind::NegCtrl},
    {"#dim", Token::Kind::Dim},
    {"durationof", Token::Kind::DurationOf},
    {"delay", Token::Kind::Delay},
    {"reset", Token::Kind::Reset},
    {"measure", Token::Kind::Measure},
    {"barrier", Token::Kind::Barrier},
    {"true", Token::Kind::True},
    {"false", Token::Kind::False},
    {"im", Token::Kind::Imag},
    {"dt", Token::Kind::TimeUnitDt},
    {"ns", Token::Kind::TimeUnitNs},
    {"us", Token::Kind::TimeUnitUs},
    {"mys", Token::Kind::TimeUnitMys},
    {"ms", Token::Kind::TimeUnitMs},
    {"s", Token::Kind::S},
    {"sin", Token::Kind::Sin},
    {"cos", Token::Kind::Cos},
    {"tan", Token::Kind::Tan},
    {"exp", Token::Kind::Exp},
    {"ln", Token::Kind::Ln},
    {"sqrt", Token::Kind::Sqrt},
};

Scanner::Scanner(std::istream* in) {
  std::ostringstream oss;
  oss << in->rdbuf();
  buffer_ = std::move(oss).str();
  ptr_ = buffer_.data();
  end_ = ptr_ + buffer_.size();
  nextCh();
}

Token Scanner::next() {
  if (const auto commentToken = consumeWhitespaceAndComments()) {
    return *commentToken;
  }

  if (isFirstIdChar(ch)) {
    return consumeName();
  }
  if (isNum(ch) || (ch == '.' && isNum(peek())) ||
      (ch == '-' && isNum(peek()))) {
    return consumeNumberLiteral();
  }
  if (ch == '$') {
    return consumeHardwareQubit();
  }

  if (ch == '"' || ch == '\'') {
    return consumeString();
  }

  Token t(line, col);
  switch (ch) {
    case 0:
      t.kind = Token::Kind::Eof;
      // Here we return as we don't want to call nextCh after EOF.
      // We also don't set length, as the eof token has no length.
      return t;
    case '[':
      t.kind = Token::Kind::LBracket;
      break;
    case ']':
      t.kind = Token::Kind::RBracket;
      break;
    case '{':
      t.kind = Token::Kind::LBrace;
      break;
    case '}':
      t.kind = Token::Kind::RBrace;
      break;
    case '(':
      t.kind = Token::Kind::LParen;
      break;
    case ')':
      t.kind = Token::Kind::RParen;
      break;
    case ':':
      t.kind = Token::Kind::Colon;
      break;
    case ';':
      t.kind = Token::Kind::Semicolon;
      break;
    case '.':
      t.kind = Token::Kind::Dot;
      break;
    case ',':
      t.kind = Token::Kind::Comma;
      break;
    case '-':
      switch (peek()) {
        case '>':
          nextCh();
          t.kind = Token::Kind::Arrow;
          break;
        case '=':
          nextCh();
          t.kind = Token::Kind::MinusEquals;
          break;
        default:
          t.kind = Token::Kind::Minus;
          break;
      }
      break;
    case '+':
      switch (peek()) {
        case '=':
          nextCh();
          t.kind = Token::Kind::PlusEquals;
          break;
        case '+':
          nextCh();
          t.kind = Token::Kind::DoublePlus;
          break;
        default:
          t.kind = Token::Kind::Plus;
          break;
      }
      break;
    case '*':
      switch (peek()) {
        case '=':
          nextCh();
          t.kind = Token::Kind::AsteriskEquals;
          break;
        case '*':
          nextCh();
          if (peek() == '=') {
            nextCh();
            t.kind = Token::Kind::DoubleAsteriskEquals;
          } else {
            t.kind = Token::Kind::DoubleAsterisk;
          }
          break;
        default:
          t.kind = Token::Kind::Asterisk;
          break;
      }
      break;
    case '/':
      if (peek() == '=') {
        nextCh();
        t.kind = Token::Kind::SlashEquals;
      } else {
        t.kind = Token::Kind::Slash;
      }
      break;
    case '%':
      if (peek() == '=') {
        nextCh();
        t.kind = Token::Kind::PercentEquals;
      } else {
        t.kind = Token::Kind::Percent;
      }
      break;
    case '|':
      switch (peek()) {
        case '=':
          nextCh();
          t.kind = Token::Kind::PipeEquals;
          break;
        case '|':
          nextCh();
          t.kind = Token::Kind::DoublePipe;
          break;
        default:
          t.kind = Token::Kind::Pipe;
          break;
      }
      break;
    case '&':
      switch (peek()) {
        case '=':
          nextCh();
          t.kind = Token::Kind::AmpersandEquals;
          break;
        case '&':
          nextCh();
          t.kind = Token::Kind::DoubleAmpersand;
          break;
        default:
          t.kind = Token::Kind::Ampersand;
          break;
      }
      break;
    case '^':
      if (peek() == '=') {
        nextCh();
        t.kind = Token::Kind::CaretEquals;
      } else {
        t.kind = Token::Kind::Caret;
      }
      break;
    case '~':
      if (peek() == '=') {
        nextCh();
        t.kind = Token::Kind::TildeEquals;
      } else {
        t.kind = Token::Kind::Tilde;
      }
      break;
    case '!':
      if (peek() == '=') {
        nextCh();
        t.kind = Token::Kind::NotEquals;
      } else {
        t.kind = Token::Kind::ExclamationPoint;
      }
      break;
    case '<':
      switch (peek()) {
        case '=':
          nextCh();
          t.kind = Token::Kind::LessThanEquals;
          break;
        case '<':
          nextCh();
          if (peek() == '=') {
            nextCh();
            t.kind = Token::Kind::LeftShitEquals;
          } else {
            t.kind = Token::Kind::LeftShift;
          }
          break;
        default:
          t.kind = Token::Kind::LessThan;
          break;
      }
      break;
    case '>':
      switch (peek()) {
        case '=':
          nextCh();
          t.kind = Token::Kind::GreaterThanEquals;
          break;
        case '>':
          nextCh();
          if (peek() == '=') {
            nextCh();
            t.kind = Token::Kind::RightShiftEquals;
          } else {
            t.kind = Token::Kind::RightShift;
          }
          break;
        default:
          t.kind = Token::Kind::GreaterThan;
          break;
      }
      break;
    case '=':
      if (peek() == '=') {
        nextCh();
        t.kind = Token::Kind::DoubleEquals;
      } else {
        t.kind = Token::Kind::Equals;
      }
      break;
    case '@':
      t.kind = Token::Kind::At;
      break;
    default: {
      error("Unknown character '" + std::to_string(ch) + "'");
      t.kind = Token::Kind::None;
      nextCh();
      break;
    }
  }

  nextCh();

  t.endCol = col;
  t.endLine = line;
  return t;
}
}  // namespace qasm
