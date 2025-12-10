#include "unity.h"
#include "rf_metrics.h"

// Mocks necesarios
#include "mock_psd.h"
#include "mock_datatypes.h"
#include "mock_sdr_HAL.h"

void setUp(void) {}
void tearDown(void) {}

// --- TEST 1: Calcula correctamente nperseg y noverlap ---
void test_find_params_psd_basic()
{
    DesiredCfg_t desired = {
        .window_type = 1,
        .sample_rate = 2000000,   // 2 MHz
        .rbw = 1000,              // 1 kHz
        .center_freq = 100000000, // 100 MHz
        .span = 2000000,
        .overlap = 0.5,
        .amp_enabled = 1,
        .lna_gain = 20,
        .vga_gain = 10,
        .ppm_error = 0
    };

    SDR_cfg_t hack_cfg;
    PsdConfig_t psd_cfg;
    RB_cfg_t rb_cfg;

    // --- EXPECTATIVA: llamada a get_window_enbw_factor() ---
    get_window_enbw_factor_ExpectAndReturn(desired.window_type, 1.5);  
    // ejemplo: Hanning window ~1.5 ENBW

    // Ejecutar
    int rc = find_params_psd(desired, &hack_cfg, &psd_cfg, &rb_cfg);

    TEST_ASSERT_EQUAL(0, rc);

    double required = 1.5 * (double)desired.sample_rate / (double)desired.rbw;
    int exponent = (int)ceil(log2(required));
    int expected_nperseg = (int)pow(2, exponent);

    TEST_ASSERT_EQUAL(expected_nperseg, psd_cfg.nperseg);
    TEST_ASSERT_EQUAL(expected_nperseg * desired.overlap, psd_cfg.noverlap);

    TEST_ASSERT_EQUAL(desired.window_type, psd_cfg.window_type);
    TEST_ASSERT_EQUAL(desired.sample_rate, psd_cfg.sample_rate);

    // Revisar hack_cfg
    TEST_ASSERT_EQUAL(desired.sample_rate, hack_cfg.sample_rate);
    TEST_ASSERT_EQUAL(desired.center_freq, hack_cfg.center_freq);
    TEST_ASSERT_EQUAL(desired.amp_enabled, hack_cfg.amp_enabled);
    TEST_ASSERT_EQUAL(desired.lna_gain, hack_cfg.lna_gain);
    TEST_ASSERT_EQUAL(desired.vga_gain, hack_cfg.vga_gain);
    TEST_ASSERT_EQUAL(desired.ppm_error, hack_cfg.ppm_error);

    // Revisar ring buffer config
    TEST_ASSERT_EQUAL(desired.sample_rate * 2, rb_cfg.total_bytes);
    TEST_ASSERT_EQUAL(rb_cfg.total_bytes * 2, rb_cfg.rb_size);
}
