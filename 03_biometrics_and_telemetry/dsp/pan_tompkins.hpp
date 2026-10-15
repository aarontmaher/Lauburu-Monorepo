#pragma once

#include <cstdint>
#include <cstddef>
#include <vector>
#include <string>

namespace lauburu {
namespace dsp {

// Standard header for binary mapped ECG data
struct ECGDataHeader {
    uint32_t magic; // Should be 0x45434731 "ECG1"
    uint32_t sample_rate;
    uint64_t num_samples;
};

class PanTompkins {
public:
    // Initialize with expected sample rate (e.g. 512 for Movesense)
    PanTompkins(int sample_rate = 512);
    ~PanTompkins() = default;

    // Reset internal state for streaming or new file
    void reset();

    // Process a single sample
    // Returns the integrated signal value
    float process_sample(float ecg_sample);

    // Process a memory mapped file containing raw ECG data (float array)
    // Evaluates QRS and writes peak indices (uint64_t) to an output file
    bool process_mmap_file(const std::string& input_mmap_path, const std::string& output_peaks_path);

private:
    int fs;
    
    // Low pass filter
    std::vector<float> x_lpf;
    std::vector<float> y_lpf;
    int ptr_lpf;

    // High pass filter
    std::vector<float> x_hpf;
    std::vector<float> y_hpf;
    int ptr_hpf;

    // Derivative filter
    std::vector<float> x_der;
    int ptr_der;

    // Moving window integration
    std::vector<float> x_mwi;
    int ptr_mwi;
    float mwi_sum;
    int mwi_window_size;

    // Filter delay parameters scaled dynamically by sample rate
    int lpf_d1, lpf_d2;
    int hpf_d1, hpf_d2, hpf_d3;
    int der_d1, der_d2;
};

} // namespace dsp
} // namespace lauburu
