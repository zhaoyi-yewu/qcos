#encoding=utf-8
from pytest import fixture
from qcos.cna import *

@fixture
def awg_ins():
    awgConfig = {
        'product': "M3201A",
        'serialNumber': "MY63400261",
        'channelList': [1,2,3,4],
        'waveFileDir': "./wave_file",
        'wave_id_file': './wave_id.json',
        'amp': 0.5,
        'addr_ip': '192.168.1.151'
    }
    res = AWGMocker(name="scan_awg", awgConfig=awgConfig)
    return res

@fixture
def nido():
    return NI(
        "scan_nido",
        dev = ["/dev2/port0/line0:7",  "/dev2/port1/line0:3", "/dev2/port2/line6", "/dev2/port3/line2", "/dev2/port3/line3", "/dev2/port3/line6"],
        type = 2,
        rate = 5e5,
    )

@fixture
def niao():
    return NI(
        "scan_niao",
        dev = ["/dev1/ao0", "/dev1/ao3", "/dev1/ao4", "/dev1/ao7", "/dev1/ao8", "/dev1/ao9", "/dev1/ao15"],
        type = 2,
        rate = 4e5,
        num_samples = 1, 
        trigger_source="/dev1/PFI0",
    )

@fixture
def camera_ins():
    return get_real_camera(dll_path="<fake>", init_path = "./", calib_img_path = 'test/calib.png', w_off=872, h_off = 856)

def test_scan_do0_meas_cooling_time(awg_ins, nido, niao, camera_ins):
    res = scan_do0_meas_cooling_time(awg_ins, nido, niao, camera_ins, 5, 10, 0, 1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_do0_pgc_cooling_time(awg_ins, nido, niao, camera_ins):
    res = scan_do0_pgc_cooling_time(awg_ins, nido, niao, camera_ins, 5, 10, 0, 1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_do2_meas_pump_time(awg_ins, nido, niao, camera_ins):
    res = scan_do2_meas_pump_time(awg_ins, nido, niao, camera_ins, 5, 10, 0, 1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_do2_pgc_pump_time(awg_ins, nido, niao, camera_ins):
    res = scan_do2_pgc_pump_time(awg_ins, nido, niao, camera_ins, 5, 10, 0, 1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao1_meas_cooling_detune(awg_ins, nido, niao, camera_ins):
    res = scan_ao1_meas_cooling_detune(awg_ins, nido, niao, camera_ins, 5, 10, 3.2, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao1_meas_cooling_freq(awg_ins, nido, niao, camera_ins):
    res = scan_ao1_meas_cooling_freq(awg_ins, nido, niao, camera_ins, 5, 10, 6.4, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao1_pgc_cooling_detune(awg_ins, nido, niao, camera_ins):
    res = scan_ao1_pgc_cooling_detune(awg_ins, nido, niao, camera_ins, 5, 10, 3.2, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao3_meas_pump_detune(awg_ins, nido, niao, camera_ins):
    res = scan_ao3_meas_pump_detune(awg_ins, nido, niao, camera_ins, 5, 10, 4, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao3_pgc_pump_detune(awg_ins, nido, niao, camera_ins):
    res = scan_ao3_pgc_pump_detune(awg_ins, nido, niao, camera_ins, 5, 10, 3.4, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao4_pgc_comp_mag(awg_ins, nido, niao, camera_ins):
    res = scan_ao4_pgc_comp_mag(awg_ins, nido, niao, camera_ins, 5, 10, 3.4, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao5_pgc_comp_mag(awg_ins, nido, niao, camera_ins):
    res = scan_ao5_pgc_comp_mag(awg_ins, nido, niao, camera_ins, 5, 10, 3.4, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao6_pgc_comp_mag(awg_ins, nido, niao, camera_ins):
    res = scan_ao6_pgc_comp_mag(awg_ins, nido, niao, camera_ins, 5, 10, 3.4, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao7_raman_source_freq(awg_ins, nido, niao, camera_ins):
    res = scan_ao7_raman_source_freq(awg_ins, nido, niao, camera_ins, 5, 10, 3.4, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao8_pgc_pump_amp(awg_ins, nido, niao, camera_ins):
    res = scan_ao8_pgc_pump_amp(awg_ins, nido, niao, camera_ins, 5, 10, 5, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao8_meas_pump_amp(awg_ins, nido, niao, camera_ins):
    res = scan_ao8_meas_pump_amp(awg_ins, nido, niao, camera_ins, 5, 10, 5, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_ao9_pgc_cooling_amp(awg_ins, nido, niao, camera_ins):
    res = scan_ao9_pgc_cooling_amp(awg_ins, nido, niao, camera_ins, 5, 10, 4.8, 0.1, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_raman_cpmg(awg_ins, nido, niao, camera_ins):
    res = scan_raman_cpmg(awg_ins, nido, niao, camera_ins, 5, 10, 10e-6, 1e-6, 1, 10,  niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_raman_rabi(awg_ins, nido, niao, camera_ins):
    res = scan_raman_rabi(awg_ins, nido, niao, camera_ins, 5, 10, 12e-6, 1e-6, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_raman_ch1(awg_ins, nido, niao, camera_ins):
    res = scan_raman_ch1(awg_ins, nido, niao, camera_ins, 5, 10, 100e6, 1e5, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_raman_ch2(awg_ins, nido, niao, camera_ins):
    res = scan_raman_ch2(awg_ins, nido, niao, camera_ins, 5, 10, 100e6, 1e5, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_raman_ramsey(awg_ins, nido, niao, camera_ins):
    res = scan_raman_ramsey(awg_ins, nido, niao, camera_ins, 5, 10, 10e-6, 1e-6, 1, 10,  niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_arrange_amp(awg_ins, nido, niao, camera_ins):
    res = scan_arrange_amp(awg_ins, nido, niao, camera_ins, 3, 6, 9, 11, 80.95e6, 1e5, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_arrange_ch1(awg_ins, nido, niao, camera_ins):
    res = scan_arrange_ch1(awg_ins, nido, niao, camera_ins, 3, 6, 9, 11, 80.95e6, 1e5, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_arrange_ch2(awg_ins, nido, niao, camera_ins):
    res = scan_arrange_ch2(awg_ins, nido, niao, camera_ins, 3, 6, 9, 11, 80.95e6, 1e5, 1, niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])

def test_scan_raman_spin_echo(awg_ins, nido, niao, camera_ins):
    res = scan_raman_spin_echo(awg_ins, nido, niao, camera_ins, 5, 10, 10e-6, 1e-6, 1, 10,  niter_per_scan=30, qpu_file="test/na_file.json")
    assert(res == [(0.0, 0)])
