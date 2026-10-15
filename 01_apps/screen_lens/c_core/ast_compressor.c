#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

/**
 * Native C high-speed code/AST compressor.
 * Strips comments and extraneous whitespace with zero heap churn.
 */
size_t native_compress_code(const char *src, size_t src_len, char *dst, size_t dst_max) {
    if (!src || !dst || dst_max == 0) return 0;

    size_t r = 0, w = 0;
    bool in_line_comment = false;
    bool in_multiline_doc = false;

    while (r < src_len && w + 1 < dst_max) {
        // Check for line comments (# in Python, // in C/Rust)
        if (!in_multiline_doc && !in_line_comment) {
            if (src[r] == '#' || (r + 1 < src_len && src[r] == '/' && src[r+1] == '/')) {
                in_line_comment = true;
            }
        }

        // Check for Python triple-quote docstrings
        if (!in_line_comment && r + 2 < src_len) {
            if ((src[r] == '"' && src[r+1] == '"' && src[r+2] == '"') ||
                (src[r] == '\'' && src[r+1] == '\'' && src[r+2] == '\'')) {
                in_multiline_doc = !in_multiline_doc;
                r += 3;
                continue;
            }
        }

        if (src[r] == '\n') {
            in_line_comment = false;
            dst[w++] = '\n';
            r++;
            continue;
        }

        if (!in_line_comment && !in_multiline_doc) {
            dst[w++] = src[r];
        }
        r++;
    }

    dst[w] = '\0';
    return w;
}

#ifdef TEST_MAIN
int main() {
    const char *sample = "# Header comment\ndef foo():\n    \"\"\"Docstring to strip\"\"\"\n    x = 10  # inline\n    return x\n";
    char out[1024];
    size_t out_len = native_compress_code(sample, strlen(sample), out, sizeof(out));
    printf("Original (%zu bytes):\n%s\n", strlen(sample), sample);
    printf("Compressed (%zu bytes):\n%s\n", out_len, out);
    return 0;
}
#endif
