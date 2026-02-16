#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <stdexcept>
#include <vector>

namespace py = pybind11;

// Simple EMA implementation that matches a common "adjust=False" style:
// ema[0] = x[0]
// ema[t] = alpha*x[t] + (1-alpha)*ema[t-1]
static py::array_t<double> ema_1d(py::array_t<double, py::array::c_style | py::array::forcecast> x,
                                  int span)
{
    if (span <= 0)
    {
        throw std::invalid_argument("span must be > 0");
    }

    auto buf = x.request();
    if (buf.ndim != 1)
    {
        throw std::invalid_argument("x must be a 1D array");
    }

    const auto n = static_cast<size_t>(buf.shape[0]);
    py::array_t<double> out(buf.shape[0]);
    auto out_buf = out.request();

    auto *in_ptr = static_cast<double *>(buf.ptr);
    auto *out_ptr = static_cast<double *>(out_buf.ptr);

    if (n == 0)
    {
        return out;
    }

    const double alpha = 2.0 / (static_cast<double>(span) + 1.0);

    out_ptr[0] = in_ptr[0];
    for (size_t i = 1; i < n; i++)
    {
        out_ptr[i] = alpha * in_ptr[i] + (1.0 - alpha) * out_ptr[i - 1];
    }

    return out;
}

PYBIND11_MODULE(_fast_indicators, m)
{
    m.doc() = "Fast indicators implemented in C++ (pybind11)";

    m.def(
        "ema",
        &ema_1d,
        py::arg("x"),
        py::arg("span"),
        "Compute EMA for a 1D array (adjust=False style).");
}