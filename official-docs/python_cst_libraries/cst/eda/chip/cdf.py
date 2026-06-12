# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

CDF_DEFAULT = """
(
    promptWidth 175 
    fieldHeight 35 
    fieldWidth 350 
    buttonFieldWidth 340 
    formInitProc nil 
    doneProc nil 
    parameters nil 
    propList 
    (
        instNameType "schematic" 
        instDisplayMode "cellName" 
        netNameType "schematic" 
        termSimType "DC" 
        termDisplayMode "none" 
        paramSimType "DC" 
        paramDisplayMode "parameter" 
        viewInfo (nil) 
        simInfo 
        (
            nil 
            spectre 
            (
                nil 
                modelParamExprList nil 
                optParamExprList nil 
                opParamExprList nil 
                stringParameters nil 
                propMapping nil 
                termMapping nil
                termOrder nil
                componentName nil 
                instParameters nil 
                otherParameters nil 
                netlistProcedure nil
            ) 
            hspiceD 
            (
                nil 
                opParamExprList nil 
                optParamExprList nil 
                propMapping nil 
                termMapping nil 
                termOrder nil 
                namePrefix "" 
                componentName nil 
                instParameters nil 
                otherParameters nil 
                netlistProcedure nil
            ) 
            auLvs 
            (
                nil 
                namePrefix "" 
                permuteRule "" 
                propMapping nil 
                deviceTerminals "" 
                termOrder nil 
                componentName nil 
                instParameters nil
                otherParameters nil
                netlistProcedure nil
            ) 
            auCdl (
                nil
                dollarEqualParams nil
                dollarParams nil
                modelName "" 
                namePrefix "" 
                propMapping nil
                termOrder nil
                componentName nil
                instParameters nil
                otherParameters nil
                netlistProcedure nil
            ) 
            ams 
            (
                nil
                isPrimitive nil
                extraTerminals nil
                propMapping nil
                termMapping nil
                termOrder nil
                componentName nil
                excludeParameters nil
                arrayParameters nil
                stringParameters nil
                referenceParameters nil
                enumParameters nil
                instParameters nil
                otherParameters nil
                netlistProcedure nil
            )
        )
    )
)
"""

class Lict:
    def __init__(self, vals=None):
        if vals is None:
            vals = list()
        super().__setattr__('_vals', vals)

    def append(self, val):
        self._vals.append(val)

    def _pprint(self, vals, lvl=0):
        for v in vals:
            if isinstance(v, Lict):
                print("  " * lvl + "(")
                self._pprint(v, lvl=lvl+1)
                print("  " * lvl + ")")
            else:
                print("  " * lvl + str(v))

    def pprint(self):
        self._pprint(self._vals)

    def _convert_value(self, value):        
        if isinstance(value, list):
            vlist = []
            for v in value:
                vlist.append(self._convert_value(v))
            return Lict(vlist)

        elif isinstance(value, dict):
            vlist = []
            for k, v in value.items():
                vlist.append(k)
                vlist.append(self._convert_value(v))
            return Lict(vlist)

        return value

    def __str__(self) -> str:        
        return "(" + " ".join([str(v) for v in self._vals]) + ")"

    def __len__(self):
        return len(self._vals)

    def as_list(self):
        return self._vals

    def _get_key_index(self, key):
        i = self._vals.index(key)
        if not i < len(self._vals) - 1:
            raise KeyError("Not a proper Key-Value pair")            
        return i

    def __getitem__(self, key):        
        if isinstance(key, int):
            return self._vals[key]
        try:
            return self.__getattr__(key)
        except:
            raise AttributeError(f"No such attribute {key}")        
        
    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __eq__(self, other):
        if isinstance(other, list):
            return self._vals == other
        elif isinstance(other, Lict):
            return self._vals == other._vals
        return False

    def __setattr__(self, key, value):        
        cvalue = self._convert_value(value)
        if isinstance(key, int):
            self._vals[key] = cvalue
            return
        try:            
            i = self._vals.index(key)
            self._vals[i+1] = cvalue
        except ValueError:
            self._vals.extend([key, cvalue])        

    def __getattr__(self, key):        
        return self._vals[self._get_key_index(key) + 1]        
 
    def __repr__(self):
        return 'Lict(' + str(self._vals) + ')'

def _create_nested_CDF(tokens):
    res = CDF()
    it = iter(tokens)
     
    def impl(stack):
        while True:
            val = next(it, None)            
            if val is None:
                break

            if val == '(':
                stack.append(CDF())
                impl(stack)
            elif val == ')':
                popped = stack.pop()
                stack[-1].append(popped)
            elif val == 'nil':
                stack[-1].append(None)
            else:                
                stack[-1].append(val)
            
        
    stack = [res]
    impl(stack)
    return res

class CDF(Lict):
    @staticmethod
    def loads(s):
        
        import re
        s = s.strip()
        if s.startswith('(') and s.endswith(')'):
            s = s[1:-1]
        parts = re.split(r'(\(|\)|"[^"]*"|[^\s\n{}\(\)\[\]]+)', s)
        parts = [p.strip().replace('\\', '') for p in parts if p and p.strip()]

        return _create_nested_CDF(parts)

    def __str__(self) -> str:        
        svals = []
        for v in self._vals:
            cv = v
            if v is None:
                cv = 'nil'
            svals.append(str(cv))
        res = '(' + " ".join(svals) + ')'
        res = res.replace('( ',  '(')
        res = res.replace(' )',  ')')
        return res

def create_default_cdfData():
    return CDF.loads(CDF_DEFAULT)

def create_parameter(name, defValue='', choices=None):
    def surround_in_quotes(string): 
        if not string:
            return '""'       
        if not string.startswith('"'):
            string = '"' + string
        if not string.endswith('"'):
            string += '"'
        return string

    res = CDF()
    res.storeDefault = surround_in_quotes('no')
    res.choices = choices
    res.defValue = surround_in_quotes(defValue)
    res.name = surround_in_quotes(name)
    res.type = surround_in_quotes('cyclic')
    res.parseAsCEL = surround_in_quotes('no')
    res.parseAsNumber = surround_in_quotes('no')
    res.prompt = surround_in_quotes(name)
    res.units = surround_in_quotes('')
    res.propList = None

    return res


