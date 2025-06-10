from qcos.cna.core.emccd import *
import os

class TestCamera():
    
    def test_camera_mocker(self):
        
        camera_ins = get_camera_mocker()
        camera_ins.camera.set_temperature(10)
        t = camera_ins.camera.get_temperature()
        assert t == 10
        assert len(camera_ins.ion_position_list) == 200
        camera_ins.camera.start_acquisition()
        camera_ins.capture_image()
        assert camera_ins.current_image.shape == (232, 232)
        atom = camera_ins.read_and_count()
        assert len(atom) == 200
        res = camera_ins.get_status_with_threshold(100, 3)
        assert len(res) == 200
        for v in res: assert v == 0 or v == 1
        res = camera_ins.measure_with_threshold(100)
        for v in res: assert v == 0 or v == 1
        camera_ins.save_with_box(res, camera_ins.current_image, './test.png')
        camera_ins.save_images([camera_ins.current_image], './')
        camera_ins.camera.abort_acquisition()
