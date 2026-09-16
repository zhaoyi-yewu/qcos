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

#pragma once

#include <sstream>
#include <string>
#include <unordered_map>

#include "compiler/qasm_compiler/parser/token.hpp"

namespace qasm {
class Scanner {
  std::string buffer_;
  const char* ptr_ = nullptr;
  const char* end_ = nullptr;
  static const std::unordered_map<std::string_view, Token::Kind> s_keywords;
  const std::unordered_map<std::string_view, Token::Kind>* keywords{
      &s_keywords};
  char ch = 0;
  size_t line = 1;
  size_t col = 0;

  [[nodiscard]] static bool isSpace(const char c) {
    return c == ' ' || c == '\t' || c == '\r' || c == '\n';
  }

  [[nodiscard]] static bool isFirstIdChar(const char c) {
    return isalpha(c) != 0 || c == '_';
  }

  [[nodiscard]] static bool isNum(const char c) {
    return c >= '0' && c <= '9';
  }

  [[nodiscard]] static bool isHex(const char c) {
    return isNum(c) || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
  }

  void nextCh() {
    if (ptr_ < end_) {
      ch = *ptr_++;
      if (ch == '\n') {
        col = 0;
        line++;
      } else {
        col++;
      }
    } else {
      ch = 0;
    }
  }

  [[nodiscard]] char peek() const { return (ptr_ < end_) ? *ptr_ : 0; }

  std::optional<Token> consumeWhitespaceAndComments();

  static bool isValidDigit(uint8_t base, char c);

  std::string consumeNumberLiteral(uint8_t base);

  static uint64_t parseIntegerLiteral(const std::string& str, uint8_t base);

  Token consumeNumberLiteral();

  Token consumeHardwareQubit();

  Token consumeString();

  Token consumeName();

  void error(const std::string& msg) const {
    std::cerr << "Error at line " << line << ", column " << col << ": " << msg
              << '\n';
  }

  void expect(const char expected) {
    if (ch != expected) {
      error("Expected '" + std::to_string(expected) + "', got '" + ch + "'");
    } else {
      nextCh();
    }
  }

 public:
  explicit Scanner(std::istream* in);

  explicit Scanner(const std::string& externalBuffer)
      : ptr_(externalBuffer.data()), end_(ptr_ + externalBuffer.size()) {
    nextCh();
  }

  ~Scanner() = default;

  Token next();

  // Position save/restore for fast-path lookahead (Phase 5)
  struct Checkpoint {
    const char* ptr;
    char ch;
    size_t line;
    size_t col;
  };

  [[nodiscard]] Checkpoint saveCheckpoint() const {
    return Checkpoint{ptr_, ch, line, col};
  }

  void restoreCheckpoint(const Checkpoint& cp) {
    ptr_ = cp.ptr;
    ch = cp.ch;
    line = cp.line;
    col = cp.col;
  }
};
}  // namespace qasm
