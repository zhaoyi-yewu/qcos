from qcos.cna.core.data import *
from qcos.cna import GlobalSetting

class TestData:
    
    def test_data_viewer(self):
        data_viewer(GlobalSetting.get_datapath())
    
    def test_read_data(self):
        data = raw_count(f'{GlobalSetting.get_datapath()}/207a682b3c8ab7e3479e7ce9a48e1c53.hdf5')
        assert len(data) == 3
        assert len(data[0]) == 20
        assert data[2] == 'Frequency'
    
    def test_ave_data(self):
        data = average(f'{GlobalSetting.get_datapath()}/207a682b3c8ab7e3479e7ce9a48e1c53.hdf5')
        assert len(data[0]) == 20
        assert len(data[1]) == 20
        assert len(data[1][0]) == 1
        
    def test_rabi_fit(self):
        p = rabi_fit(f'{GlobalSetting.get_datapath()}/2f40db0d40d5405f5066f40ab6c18053.hdf5', bounds=(0, np.inf),
                     save_fig=True)
        assert len(p) == 4
    
    def test_gauss_fit(self):
        p = gaussian_fit(f'{GlobalSetting.get_datapath()}/207a682b3c8ab7e3479e7ce9a48e1c53.hdf5', ion_number=4,
                         plot_figure=True, save_fig=True)
        assert len(p) == 4
        assert len(p[0]) == 3
    
    def test_universal_fit(self):
        x_data, y_data = average(f'{GlobalSetting.get_datapath()}/207a682b3c8ab7e3479e7ce9a48e1c53.hdf5')
        y_data = [v[0] for v in y_data]
        assert len(x_data) == len(y_data)
        
        def my_fit(x,a,mu,sigma):
            return a*np.exp(-(x-mu)**2/(2*sigma**2))

        a0 = max(y_data)
        a1 = x_data[np.argmax(y_data)]
        #a2 = np.std(ydata)
        a2 = np.std(y_data) * (x_data[1] - x_data[0]) / a0
        p0 = [a0, a1, a2]
        p = universal_fit(x_data, y_data, my_fit, p0, 'my_fit', save_fig=True)
        assert len(p) == 3