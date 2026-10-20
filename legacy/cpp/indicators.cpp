#include <cmath>
#include <cstddef>
extern "C" int sma(const double* values, std::size_t n, std::size_t window, double* out) {
    if (!values || !out || window == 0) return 1;
    double sum = 0;
    for (std::size_t i = 0; i < n; ++i) {
        if (!std::isfinite(values[i])) return 2;
        sum += values[i];
        if (i >= window) sum -= values[i-window];
        out[i] = i+1 >= window ? sum/window : NAN;
    }
    return 0;
}
