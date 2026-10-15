#include "pan_tompkins.hpp"
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <iostream>
#include <fstream>
#include <cmath>
#include <stdexcept>
#include <algorithm>

namespace lauburu {
namespace dsp {

PanTompkins::PanTompkins(int sample_rate) : fs(sample_rate) {
    // Standard Pan-Tompkins is designed for 200 Hz. 
    // We scale the sample delays for other frequencies natively.
    float scale = static_cast<float>(fs) / 200.0f;
    
    // LPF: y(n) = 2y(n-1) - y(n-2) + x(n) - 2x(n-6) + x(n-12)
    lpf_d1 = static_cast<int>(6 * scale);
    lpf_d2 = static_cast<int>(12 * scale);
    
    // HPF: y(n) = y(n-1) - x(n)/32 + x(n-16) - x(n-17) + x(n-32)/32
    hpf_d1 = static_cast<int>(16 * scale);
    hpf_d2 = static_cast<int>(17 * scale);
    hpf_d3 = static_cast<int>(32 * scale);
    
    // Derivative: simplified to multi-sample difference
    der_d1 = static_cast<int>(1 * scale);
    der_d2 = static_cast<int>(2 * scale);
    
    // Moving window of ~150ms
    mwi_window_size = static_cast<int>(0.150f * fs); 

    x_lpf.resize(lpf_d2 + 1, 0.0f);
    y_lpf.resize(3, 0.0f); 
    ptr_lpf = 0;

    x_hpf.resize(hpf_d3 + 1, 0.0f);
    y_hpf.resize(2, 0.0f);
    ptr_hpf = 0;

    x_der.resize(der_d2 * 2 + 1, 0.0f);
    ptr_der = 0;

    x_mwi.resize(mwi_window_size, 0.0f);
    ptr_mwi = 0;
    mwi_sum = 0.0f;
}

void PanTompkins::reset() {
    std::fill(x_lpf.begin(), x_lpf.end(), 0.0f);
    std::fill(y_lpf.begin(), y_lpf.end(), 0.0f);
    ptr_lpf = 0;

    std::fill(x_hpf.begin(), x_hpf.end(), 0.0f);
    std::fill(y_hpf.begin(), y_hpf.end(), 0.0f);
    ptr_hpf = 0;

    std::fill(x_der.begin(), x_der.end(), 0.0f);
    ptr_der = 0;

    std::fill(x_mwi.begin(), x_mwi.end(), 0.0f);
    ptr_mwi = 0;
    mwi_sum = 0.0f;
}

float PanTompkins::process_sample(float x) {
    // 1. Low Pass Filter
    x_lpf[ptr_lpf] = x;
    int idx_lpf_d1 = (ptr_lpf - lpf_d1 + x_lpf.size()) % x_lpf.size();
    int idx_lpf_d2 = (ptr_lpf - lpf_d2 + x_lpf.size()) % x_lpf.size();

    float y_lpf_out = 2.0f * y_lpf[1] - y_lpf[2] + x - 2.0f * x_lpf[idx_lpf_d1] + x_lpf[idx_lpf_d2];
    y_lpf[2] = y_lpf[1];
    y_lpf[1] = y_lpf_out;
    ptr_lpf = (ptr_lpf + 1) % x_lpf.size();

    // 2. High Pass Filter
    x_hpf[ptr_hpf] = y_lpf_out;
    int idx_hpf_d1 = (ptr_hpf - hpf_d1 + x_hpf.size()) % x_hpf.size();
    int idx_hpf_d2 = (ptr_hpf - hpf_d2 + x_hpf.size()) % x_hpf.size();
    int idx_hpf_d3 = (ptr_hpf - hpf_d3 + x_hpf.size()) % x_hpf.size();

    float y_hpf_out = y_hpf[1] - (y_lpf_out / 32.0f) + x_hpf[idx_hpf_d1] - x_hpf[idx_hpf_d2] + (x_hpf[idx_hpf_d3] / 32.0f);
    y_hpf[1] = y_hpf_out;
    ptr_hpf = (ptr_hpf + 1) % x_hpf.size();

    // 3. Derivative
    x_der[ptr_der] = y_hpf_out;
    int idx_der_d1 = (ptr_der - der_d1 + x_der.size()) % x_der.size();
    int idx_der_d2 = (ptr_der - der_d2 + x_der.size()) % x_der.size();
    
    // Scale standard PT derivative for new delay map
    float y_der_out = (2.0f * x_der[ptr_der] + x_der[idx_der_d1] - x_der[idx_der_d2] - 2.0f * x_der[(ptr_der - der_d2 - der_d1 + x_der.size()) % x_der.size()]) / 8.0f;
    ptr_der = (ptr_der + 1) % x_der.size();

    // 4. Squaring
    float y_sqr = y_der_out * y_der_out;

    // 5. Moving Window Integration
    mwi_sum -= x_mwi[ptr_mwi];
    mwi_sum += y_sqr;
    x_mwi[ptr_mwi] = y_sqr;
    ptr_mwi = (ptr_mwi + 1) % x_mwi.size();

    return mwi_sum / static_cast<float>(mwi_window_size);
}

bool PanTompkins::process_mmap_file(const std::string& input_mmap_path, const std::string& output_peaks_path) {
    int fd = open(input_mmap_path.c_str(), O_RDONLY);
    if (fd < 0) {
        std::cerr << "Failed to open input file: " << input_mmap_path << std::endl;
        return false;
    }

    struct stat sb;
    if (fstat(fd, &sb) < 0) {
        close(fd);
        return false;
    }

    if (sb.st_size < static_cast<off_t>(sizeof(ECGDataHeader))) {
        std::cerr << "File too small for header." << std::endl;
        close(fd);
        return false;
    }

    void* map = mmap(nullptr, sb.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (map == MAP_FAILED) {
        std::cerr << "Memory mapping failed." << std::endl;
        close(fd);
        return false;
    }

    const ECGDataHeader* header = static_cast<const ECGDataHeader*>(map);
    if (header->magic != 0x45434731) { // "ECG1"
        std::cerr << "Invalid magic number in header." << std::endl;
        munmap(map, sb.st_size);
        close(fd);
        return false;
    }

    size_t expected_size = sizeof(ECGDataHeader) + header->num_samples * sizeof(float);
    if (sb.st_size < static_cast<off_t>(expected_size)) {
        std::cerr << "File size mismatch with header samples." << std::endl;
        munmap(map, sb.st_size);
        close(fd);
        return false;
    }

    const float* ecg_samples = reinterpret_cast<const float*>(static_cast<const char*>(map) + sizeof(ECGDataHeader));

    std::vector<uint64_t> peaks;
    
    float threshold = 0.0f; 
    int refractory_counter = 0;
    int refractory_period = static_cast<int>(0.2f * fs); // 200ms refractory
    
    // Adaptive thresholds
    float spk_i = 0.0f;
    float npk_i = 0.0f;
    
    reset();

    for (uint64_t i = 0; i < header->num_samples; ++i) {
        float mwi_val = process_sample(ecg_samples[i]);
        
        // Train during first 2 seconds
        if (i < static_cast<uint64_t>(2 * fs)) {
            if (mwi_val > threshold) {
                threshold = mwi_val;
            }
            if (i == static_cast<uint64_t>(2 * fs) - 1) {
                spk_i = threshold;
                npk_i = 0.5f * threshold;
                threshold = npk_i + 0.25f * (spk_i - npk_i);
            }
            continue;
        }

        if (refractory_counter > 0) {
            refractory_counter--;
            continue;
        }

        if (mwi_val > threshold) {
            peaks.push_back(i);
            refractory_counter = refractory_period;
            spk_i = 0.125f * mwi_val + 0.875f * spk_i;
        } else {
            npk_i = 0.125f * mwi_val + 0.875f * npk_i;
        }
        
        threshold = npk_i + 0.25f * (spk_i - npk_i);
    }

    munmap(map, sb.st_size);
    close(fd);

    // Write R-peaks
    std::ofstream out(output_peaks_path, std::ios::binary);
    if (!out) {
        std::cerr << "Failed to open output path." << std::endl;
        return false;
    }
    
    // Prefix output with the number of peaks found for easy downstream reading (e.g. DFA-alpha1 evaluation)
    uint64_t num_peaks = peaks.size();
    out.write(reinterpret_cast<const char*>(&num_peaks), sizeof(num_peaks));
    
    for (auto peak : peaks) {
        out.write(reinterpret_cast<const char*>(&peak), sizeof(peak));
    }
    out.close();

    return true;
}

} // namespace dsp
} // namespace lauburu
