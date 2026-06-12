# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

from re import sub
from cst.eda.chip.cdf import create_default_cdfData, CDF, create_parameter
import os
import cst.eda.chip as chip

from collections import defaultdict, namedtuple

def _nport_statement(snp_file, terms):
    terms_to_gnd = ['0'] * 2 * len(terms)
    for i in range(len(terms)):
        terms_to_gnd[2*i] = terms[i]

    return f'''x0 ({" ".join(terms_to_gnd)}) nport file="{snp_file}"'''

def _nport_subckt(snp_file, subckt_name, terms):
    nps = _nport_statement(snp_file, terms)
    return spectre_subckt(subckt_name, terms, nps)

def spectre_subckt(subckt_name, terms, content):
    res = f"""
simulator lang=spectre

subckt {subckt_name} {" ".join(terms)}
{content}
ends {subckt_name}
"""
    return res.strip().replace(r'\r\n', r'\n')    

def _get_snp_portnames(snp_file):
    if not os.path.exists(snp_file):
        raise FileNotFoundError(snp_file)
    
    snp_json_file = os.path.join(snp_file + ".json")
    if os.path.exists(snp_json_file):
        import json
        with open(snp_json_file) as fjson:
            snp_json = json.load(fjson)
            port_names = snp_json.get('port_names')
            if port_names:
                return port_names

    # fallback
    snp = os.path.splitext(snp_file)[-1]
    import re
    m_snp = re.match(".s([0-9]+)p", snp)
    if not m_snp:
        raise RuntimeError(f"Could not determine port names from TOUCHTONE file {snp_file}. It does not end with .s[0-9]+p")

    n = m_snp[1]
    res = []
    for i in range(int(n)):
        res.append(f'p{i}')
    return res


def create_snp_spectre_scs(snp_file, subckt_name, dest):
    import shutil
    CSTSpectreInfo = namedtuple('CSTSpectreInfo', 'file subckt terms')
    
    port_names = _get_snp_portnames(snp_file)

    snp_dest = os.path.join(dest, "cst_results")
    os.makedirs(snp_dest, exist_ok=True)
    snp_file = shutil.copy2(snp_file, snp_dest)
    snp_rel_path = os.path.relpath(snp_file, dest)
    from pathlib import PurePath
    snp_file = PurePath(snp_file)
    snp_rel_path = snp_file.relative_to(dest)

    spectre_scs = os.path.join(dest, "spectre.scs")

    with open(spectre_scs, 'w', newline='') as fscs:
        fscs.write(_nport_subckt("./" + snp_rel_path.as_posix(), subckt_name, port_names))

    return CSTSpectreInfo(file=spectre_scs, subckt=subckt_name, terms=port_names)


def read_parameters_from_txt_file(txt_file):
    with open(txt_file, 'r') as f:
        contents = f.read()        
    parameters = contents.split()
    
    res = {}
    for par in parameters:
        if not '=' in par:
            continue
        parname, value = par.split('=', 1)
        res[parname] = value

    return res
        

def create_parametric_spectre_scs(snp_folder, subckt_name, dest):
    import shutil
    CSTSpectreInfo = namedtuple('CSTSpectreInfo', 'file subckt terms params')

    import glob
    snp_files = glob.glob(os.path.join(snp_folder, "*.s*p"))
    if not snp_files:
        raise RuntimeError("There are no touchtone files in the given directory")

    snp_dest = os.path.join(dest, "cst_results")
    shutil.copytree(snp_folder, snp_dest)
            
    # get the list of snp_files in the new location
    snp_files = glob.glob(os.path.join(snp_dest, "*.s*p"))
    port_names = _get_snp_portnames(snp_files[0])
    all_pars = defaultdict(list)    
    spectre_contents = []
    for snp_file in snp_files:
        filename = os.path.splitext(snp_file)[0]
        parameter_txt = filename + "-parameter.txt"
        pars = read_parameters_from_txt_file(parameter_txt)        

        if not all_pars:
            for parname, value in pars.items():
                all_pars[parname].append(float(value))
        else:
            for parname, value in pars.items():
                vals = all_pars.get(parname)
                assert vals, f"{parameter_txt} describes a parameter {parname} not in the other parameter.txt files in the folder."
                vals.append(float(value))
        
        from pathlib import PurePath
        snp_file = PurePath(snp_file)
        snp_rel_path = snp_file.relative_to(dest)
        
        par_eq_vals = []
        for par, val in pars.items():
            par_eq_vals.append(par + '==' + val)

        par_eq_vals_and = " && ".join(par_eq_vals)
        if_statement = f"""if ({par_eq_vals_and}) {{"""
        nps = "  " + _nport_statement("./" + snp_rel_path.as_posix(), port_names)
        spectre_contents.append(if_statement)
        spectre_contents.append(nps)
        spectre_contents.append("}")

    spectre_scs = os.path.join(dest, "spectre.scs")
    with open(spectre_scs, 'w', newline='') as fscs:
        parameters = "parameters " + " ".join(all_pars.keys())
        spectre_contents.insert(0, parameters)
        content = "\n".join(spectre_contents)    
        fscs.write(spectre_subckt(subckt_name, port_names, content))

    for par, vals in all_pars.items():
        all_pars[par] = sorted(list(set(vals)))

    return CSTSpectreInfo(file=spectre_scs, subckt=subckt_name, terms=port_names, params=all_pars)    


def create_spectre_view(dest, libname, cellname, viewname, pins=None):
    d = { 
        "libroot": dest,
        "lib": libname,
        "cell": cellname,
        "view": viewname,
    }

    if pins:
        d["pins"] = pins

    return chip.create_netlist_view(d)

class SpectreViewCreator:
    def __init__(self, libpath, cellname):
        self.libroot = libroot = os.path.dirname(libpath)
        self.libname = libname = os.path.basename(libpath)
        self.cellname = cellname

        import tempfile
        self.tmpdir = td = tempfile.TemporaryDirectory()
        lib_defs = os.path.join(td.name, 'lib.defs')
        chip.open_database(str(lib_defs))

        self.spectre_view_name = "cst_spectre"
        view_dest = os.path.join(libpath, cellname, self.spectre_view_name)
        if os.path.exists(view_dest) and os.listdir(view_dest):
            raise FileExistsError(f"View already exists {libname}/{cellname}/{self.spectre_view_name}")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        chip.close_database()

    def symbol_exists(self):
        return chip.item_exists(self.libname, self.cellname, "symbol")

    def create(self, pins=None):
        return create_spectre_view(self.libroot, self.libname, self.cellname, self.spectre_view_name, pins=pins)  
    
    def get_cdfData(self):        
        cdfData_string = chip.get_cdfData(self.libname, self.cellname)
        if cdfData_string:
            return CDF.loads(cdfData_string)
        else:
            return create_default_cdfData()

    def set_cdfData(self, cdfData):
        cdf_now = str(cdfData)
        chip.set_cdfData(self.libname, self.cellname, cdf_now)

def create_cst_spectre_view_spar_non_parametric(snp_file, libpath, cellname):
    assert os.path.exists(snp_file)    
    assert os.path.isfile(snp_file), f"No such file {snp_file}"

    with SpectreViewCreator(libpath, cellname) as view:
        # check if symbol view exists, it not, it will have to be created, for which we need terminal names
        pin_specs  = None
        if not view.symbol_exists():
            pin_specs = _get_snp_portnames(snp_file)
        
        view_path = view.create(pins=pin_specs)  
        cdfData = view.get_cdfData()

        cdf = cdfData.propList
        scs_info = create_snp_spectre_scs(snp_file, cellname, view_path)
        
        cdf_before = str(cdfData)
        if not cdf_before:
            cdf.simInfo.spectre.termOrder = scs_info.terms
        if not cdf.simInfo.spectre.termOrder:
            cdf.simInfo.spectre.termOrder = scs_info.terms

        cdf_now = str(cdfData)
        if cdf_now != cdf_before:
            view.set_cdfData(cdf_now)

    return view_path            

def create_cst_spectre_view_from_parameter_sweep_results(snp_folder, libpath, cellname):
    assert os.path.isdir(snp_folder), f"No such directory {snp_folder}"        
    with SpectreViewCreator(libpath, cellname) as view:
        # check if symbol view exists, it not, it will have to be created, for which we need terminal names
        assert not view.symbol_exists(), "The symbol already exists"
                    
        import glob
        snp_files = glob.glob(os.path.join(snp_folder, "*.s*p"))
        assert snp_files, f"No touchtones files found in directory: {snp_folder}"
        pin_specs = _get_snp_portnames(snp_files[0])                

        view_path = view.create(pins=pin_specs)  
        cdfData = view.get_cdfData()

        cdf = cdfData.propList
        subckt_name = cellname

        scs_info = create_parametric_spectre_scs(snp_folder, subckt_name, view_path)

        cdf_parameters = list()
        parnames = []
        for parname, choices in scs_info.params.items():
            parnames.append(f'"{parname}"')
            choices = [f'"{v}"' for v in choices]
            cdf_parameter = create_parameter(parname, defValue=choices[0], choices=choices)
            cdf_parameters.append(cdf_parameter)
            
        cdfData.parameters = cdf_parameters

        # view_info.append(None)    
        view_info = CDF()
        view_info.parameterList = parnames
        cdf.viewInfo = [None, view.spectre_view_name, view_info]    
        cdf.simInfo.spectre.termOrder = scs_info.terms
        cdf.simInfo.spectre.instParameters = list(scs_info.params.keys())

        view.set_cdfData(cdfData)

    return view_path            




  