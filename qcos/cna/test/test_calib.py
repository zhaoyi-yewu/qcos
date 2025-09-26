from qcos.cna import *
import time

class TestCalib():
    
    loadion = LoadIonExp()
    detec = DetectionExp()
    doppler = DopplerExp()
    eit = EITExp()
    pumping = PumpingExp()
    modefreq = ModeFrequencyExp()
    sidebc = SideBandCoolingExp()
    
    def setup_method(self):
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)
    
    def teardown_method(self):
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)

    
    def test_build_dg(self):
        calb = Calibration(0, [self.loadion, self.detec, self.doppler, self.eit, self.pumping, self.modefreq, self.sidebc])
        calb.build_dg()
        assert len(calb.dg.nodes) == 7
        assert len(calb.dg.edges) == 8
        scc = calb.get_scc()
        assert len(scc) == 0
        
    def test_update(self):
        calb = Calibration(0, [self.loadion, self.detec, self.doppler, self.eit, self.pumping, self.modefreq, self.sidebc])
        calb.build_dg()
        calb.update(self.sidebc)
        for node in calb.dg.nodes():
            time_threshold = calb.dg.nodes[node]['cal'].time_threshold
            if node == 'LoadIon': time_threshold = 100
            assert time.time() - calb.dg.nodes[node]['cal'].check_time < time_threshold
    
    def test_recalib(self):
        calb = Calibration(0, [self.loadion, self.detec, self.doppler, self.eit, self.pumping, self.modefreq, self.sidebc])
        calb.build_dg()
        calb.recalibrate(self.eit)
        for node in calb.dg.nodes():
            if node == 'SideBandCooling': continue
            time_threshold = calb.dg.nodes[node]['cal'].time_threshold
            if node == 'LoadIon': time_threshold = 100
            assert time.time() - calb.dg.nodes[node]['cal'].calib_time < time_threshold
    
    
    def test_calib_all(self):
        calb = Calibration(0, [self.loadion, self.detec, self.doppler, self.eit, self.pumping, self.modefreq, self.sidebc])
        calb.build_dg()
        calb.calibrate_all()
        for node in calb.dg.nodes():
            time_threshold = calb.dg.nodes[node]['cal'].time_threshold
            if node == 'LoadIon': time_threshold = 100
            assert time.time() - calb.dg.nodes[node]['cal'].calib_time < time_threshold
    