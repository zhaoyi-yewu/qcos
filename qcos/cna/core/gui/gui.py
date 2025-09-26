import traitlets
import ipyvuetify as v
import numpy as np

def is_string_float(the_string: str) -> bool:
    try:
        float(the_string)
        return True
    except ValueError:
        return False


def is_string_int(the_string: str) -> bool:
    try:
        int(the_string)
        return True
    except ValueError:
        return False

def is_string_tuple(value) -> bool:
    if isinstance(value, str):
        try:
            x = eval(value)
            return isinstance(x, tuple)
        except:
            return False
    return isinstance(value, tuple)

def all_pass(v):
    return True

class ValidatedField(v.TextField):
        _typecheck_func: callable = None
        _type = None

        num_value = None  # must determine appropriate traitlet type dynamically

        def __init__(
            self,
            v_model,
            num_type=None,
            v_min=None,
            v_max=None,
            step=None,
            filled=True,
            typecheck_func = None,
            disable = False,
            **kwargs,
        ):
            self.name = kwargs.pop("name", None)
            self._type = num_type if num_type is not None else type(v_model)
            if num_type == float or num_type == np.float64:
                TraitletClass = traitlets.Float
                self._typecheck_func = is_string_float
                self.step = step if step is not None else 0.1
            elif num_type == int:
                TraitletClass = traitlets.Int
                self._typecheck_func = is_string_int
                self.step = step if step is not None else 1
            elif num_type == tuple:
                TraitletClass = traitlets.Tuple
                self._typecheck_func = is_string_tuple
            elif num_type == str:
                TraitletClass = traitlets.Any
                self._typecheck_func = all_pass
            else:
                raise Exception(f"Not a supported number type: {num_type}")

            if typecheck_func is not None: self._typecheck_func = typecheck_func
            
            self.add_traits(
                num_value=TraitletClass(read_only=True).tag(sync=True),
            )
            if num_type == float or num_type == int:
                self.add_traits(
                    v_min=TraitletClass(allow_none=True).tag(sync=True),
                    v_max=TraitletClass(allow_none=True).tag(sync=True),
                )
            self.v_min = v_min
            self.v_max = v_max
            self.disabled = disable
            super().__init__(v_model=v_model, filled=filled, **kwargs)

        
        @traitlets.validate("v_model")
        def _validate_v_model(self, state):
            if self.is_valid():
                self.error = False
                self.rules = []
            else:
                self.error = True
                self.rules = ["invalid"]
            return state["value"]

        @traitlets.observe("v_model")
        def _observe_v_model(self, change):
            if not self.error:
                self.set_trait("num_value", self._convert_to_type(change["new"]))

        def is_valid(self):
            return self._typecheck_func(self.v_model)

        def _convert_to_type(self, value):
            if self._type == tuple and isinstance(value, str): return eval(value)
            return self._type(value)
        
def get_box_list(init_param, attr_dict = {}, callback_func = None):
    widgets = {}
    box_list = []
    for name, value in init_param.items():
        if isinstance(value, bool): continue
        if isinstance(value, (int, float, str, tuple)): 
            label_str = name
            attrs = attr_dict.get(name, {})
            widgets[name] = ValidatedField(
                v_model=value,
                num_type=type(value),
                placeholder=f"enter appropriate value for {label_str}",
                label=label_str,
                name=name,
                outlined=True,
                filled=True,
                typecheck_func = attrs.get('typecheck', None),
                dense=True,
                style_="width: 30%;",
                class_="ml-2 py-0",
                disable = attrs.get('disable', False),
            )
            widgets[name].observe(callback_func, names="v_model")
            box_list.append(widgets[name])
    return box_list

def compare_type(new_v, v):
    if isinstance(v, (bool, str, tuple, int)):
        return type(new_v) == type(v)
    elif isinstance(v, float):
        return np.isreal(new_v)
    else:
        raise TypeError(f"{type(v)} is not supported")

def set_value_by_input(obj, key):
    v = getattr(obj, key, None)
    if v is None: raise KeyError(f"{type(obj).__name__} has no attribute named {key}")
    if not isinstance(v, (bool, int, float, str, tuple)): raise TypeError(f'{key} is {type(v)}, not supported')
    
    while True:
        try:
            new_v = input(f"请输入{key}({type(v)},当前值:{v})[保持原值请输入回车]: ")
            if new_v == '': break
            if not isinstance(v, str):
                new_v = eval(new_v)
            assert type(new_v) == type(v)
            obj.__setattr__(key, new_v)
            break
        except Exception as e:
            print(f"输入类型错误，需为{type(v)}")
    
def set_all_value_by_input(obj, **kwargs):
    init_param = obj.snapshot()
    ignore = kwargs.get('ignore', [])
    for v in ignore:
        if v in init_param: init_param.pop(v)
    for name, value in init_param.items():
        if isinstance(value, (bool, int, float, str, tuple)):
             while True:
                try:
                    new_v = input(f"请输入{name}({type(value)},当前值:{value})[保持原值请输入回车]: ")
                    if new_v == '': break
                    if not isinstance(value, str):
                        new_v = eval(new_v)
                        
                    assert type(new_v) == type(value)
                    obj.__setattr__(name, new_v)
                    break
                except Exception as e:
                    print(f"输入类型错误，需为{type(value)}")