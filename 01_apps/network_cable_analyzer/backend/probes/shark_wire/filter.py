"""
Wireshark-Syntax Display Filter Tokenizer, Recursive Descent AST Parser, and Compiled Evaluator.
Evaluates in < 1 microsecond per packet without eval().
Strictly rejects Python code injection attempts.
"""

import re
from typing import Tuple, Optional, Callable, Any, Dict, List

# Banned keywords and dangerous characters for code injection prevention
BANNED_IDENTIFIERS = {
    "__import__", "eval", "exec", "open", "system", "os", "sys", "subprocess",
    "import", "lambda", "compile", "globals", "locals", "getattr", "setattr",
    "delattr", "hasattr", "builtins", "__builtins__", "__class__", "__subclasses__",
}

DANGEROUS_CHARS = set(";{}\\[]`$^~")

KNOWN_SHORTHANDS = {
    "wireguard", "wg", "http", "http2", "airpc", "ai-rpc", "sse", "tcp",
    "udp", "ssh", "dns", "icmp", "ipv4", "ipv6", "eth", "utun", "frame"
}

KNOWN_FIELDS = {
    "ip.addr", "ip.src", "ip.dst", "src_ip", "dst_ip",
    "port", "tcp.port", "udp.port", "src_port", "dst_port",
    "protocol", "len", "length", "frame.len",
    "http.method", "tcp.flags.syn", "tcp.flags",
}


class Token:
    def __init__(self, typ: str, value: Any, pos: int = 0):
        self.type = typ
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


def tokenize(expr: str) -> Tuple[Optional[List[Token]], Optional[str]]:
    """Tokenize filter expression into strict lexical tokens."""
    tokens: List[Token] = []
    i = 0
    n = len(expr)

    while i < n:
        c = expr[i]

        if c.isspace():
            i += 1
            continue

        if c in DANGEROUS_CHARS:
            return None, f"Dangerous character '{c}' rejected"

        # Parentheses
        if c == "(":
            tokens.append(Token("LPAREN", "(", i))
            i += 1
            continue
        if c == ")":
            tokens.append(Token("RPAREN", ")", i))
            i += 1
            continue

        # Logical Operators
        if expr.startswith("&&", i):
            tokens.append(Token("AND", "&&", i))
            i += 2
            continue
        if expr.startswith("||", i):
            tokens.append(Token("OR", "||", i))
            i += 2
            continue
        if expr.startswith("!=", i):
            tokens.append(Token("OP", "!=", i))
            i += 2
            continue
        if c == "!":
            tokens.append(Token("NOT", "!", i))
            i += 1
            continue

        # Comparison Operators
        if expr.startswith("==", i):
            tokens.append(Token("OP", "==", i))
            i += 2
            continue
        if expr.startswith(">=", i):
            tokens.append(Token("OP", ">=", i))
            i += 2
            continue
        if expr.startswith("<=", i):
            tokens.append(Token("OP", "<=", i))
            i += 2
            continue
        if c == ">":
            tokens.append(Token("OP", ">", i))
            i += 1
            continue
        if c == "<":
            tokens.append(Token("OP", "<", i))
            i += 1
            continue

        # Quoted string literal
        if c in ('"', "'"):
            quote = c
            start = i
            i += 1
            val_chars = []
            while i < n and expr[i] != quote:
                val_chars.append(expr[i])
                i += 1
            if i >= n:
                return None, "Unterminated string literal"
            i += 1  # skip closing quote
            val_str = "".join(val_chars)
            tokens.append(Token("VALUE", val_str, start))
            continue

        # Identifiers, numbers, IP addresses, field names
        start = i
        while i < n and (expr[i].isalnum() or expr[i] in "._:-"):
            i += 1
        word = expr[start:i]

        if not word:
            return None, f"Unexpected character at position {i}: {expr[i]}"

        # Check for banned code injection attempts
        if word.lower() in BANNED_IDENTIFIERS:
            return None, f"Malicious identifier '{word}' strictly rejected"

        word_lower = word.lower()
        if word_lower == "and":
            tokens.append(Token("AND", "and", start))
        elif word_lower == "or":
            tokens.append(Token("OR", "or", start))
        elif word_lower == "not":
            tokens.append(Token("NOT", "not", start))
        elif word_lower == "contains":
            tokens.append(Token("OP", "contains", start))
        elif word_lower in KNOWN_FIELDS:
            tokens.append(Token("FIELD", word_lower, start))
        elif word_lower in KNOWN_SHORTHANDS:
            tokens.append(Token("KEYWORD", word_lower, start))
        else:
            tokens.append(Token("VALUE", word, start))

    tokens.append(Token("EOF", "", n))
    return tokens, None


class SharkWireFilter:
    """
    Wireshark-compatible display filter engine.
    Safely compiles filter expressions into an executable predicate function.
    """

    def __init__(self, expression: str = ""):
        self.raw_expression: str = expression.strip()
        self._compiled_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
        self._is_valid: bool = False
        self._error: Optional[str] = None
        self._compile()

    def _compile(self) -> None:
        """Lex, parse, and compile the filter expression."""
        if not self.raw_expression:
            self._is_valid = True
            self._compiled_fn = lambda pkt: True
            return

        tokens, err = tokenize(self.raw_expression)
        if err or tokens is None:
            self._is_valid = False
            self._error = err or "Tokenization failed"
            return

        parser = _FilterParser(tokens)
        try:
            fn = parser.parse()
            self._compiled_fn = fn
            self._is_valid = True
            self._error = None
        except Exception as e:
            self._is_valid = False
            self._error = str(e)

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Return (is_valid, error_message)."""
        return self._is_valid, self._error

    def matches(self, packet: Dict[str, Any]) -> bool:
        """Evaluate packet against the compiled filter predicate."""
        if not self._is_valid or self._compiled_fn is None:
            return False
        try:
            return self._compiled_fn(packet)
        except Exception:
            return False


class _FilterParser:
    """Recursive descent AST parser and closure compiler."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def cur(self) -> Token:
        return self.tokens[self.pos]

    def eat(self, typ: str) -> Token:
        tok = self.cur()
        if tok.type != typ:
            raise ValueError(f"Expected token type '{typ}', got '{tok.type}' ({tok.value!r}) at pos {tok.pos}")
        self.pos += 1
        return tok

    def parse(self) -> Callable[[Dict[str, Any]], bool]:
        node = self.expr_or()
        if self.cur().type != "EOF":
            raise ValueError(f"Unexpected trailing token '{self.cur().value}' at pos {self.cur().pos}")
        return node

    def expr_or(self) -> Callable[[Dict[str, Any]], bool]:
        node = self.expr_and()
        while self.cur().type == "OR":
            self.eat("OR")
            right = self.expr_and()
            node = _make_or(node, right)
        return node

    def expr_and(self) -> Callable[[Dict[str, Any]], bool]:
        node = self.expr_unary()
        while self.cur().type == "AND":
            self.eat("AND")
            right = self.expr_unary()
            node = _make_and(node, right)
        return node

    def expr_unary(self) -> Callable[[Dict[str, Any]], bool]:
        if self.cur().type == "NOT":
            self.eat("NOT")
            child = self.expr_primary()
            return _make_not(child)
        return self.expr_primary()

    def expr_primary(self) -> Callable[[Dict[str, Any]], bool]:
        tok = self.cur()

        if tok.type == "LPAREN":
            self.eat("LPAREN")
            node = self.expr_or()
            self.eat("RPAREN")
            return node

        if tok.type == "KEYWORD":
            self.eat("KEYWORD")
            return _make_keyword_matcher(tok.value)

        if tok.type in ("FIELD", "VALUE"):
            field_tok = self.eat(tok.type)
            field_name = str(field_tok.value).lower()

            # Check if standalone value is actually a keyword
            if field_name in KNOWN_SHORTHANDS:
                return _make_keyword_matcher(field_name)

            # Expect comparison operator
            if self.cur().type != "OP":
                # Standalone field check (truthy existence)
                return _make_field_presence_matcher(field_name)

            op_tok = self.eat("OP")
            op = op_tok.value

            val_tok = self.cur()
            if val_tok.type not in ("VALUE", "FIELD", "KEYWORD"):
                raise ValueError(f"Expected comparison value after '{op}' at pos {val_tok.pos}")
            self.pos += 1
            val = val_tok.value

            return _make_comparison_matcher(field_name, op, val)

        raise ValueError(f"Unexpected token '{tok.value}' at pos {tok.pos}")


# --- Compiled Matcher Factory Functions ---

def _make_and(left: Callable, right: Callable) -> Callable:
    return lambda pkt: left(pkt) and right(pkt)


def _make_or(left: Callable, right: Callable) -> Callable:
    return lambda pkt: left(pkt) or right(pkt)


def _make_not(child: Callable) -> Callable:
    return lambda pkt: not child(pkt)


def _make_keyword_matcher(keyword: str) -> Callable[[Dict[str, Any]], bool]:
    kw = keyword.lower()
    if kw in ("wireguard", "wg"):
        return lambda pkt: (
            pkt.get("protocol") == "WireGuard"
            or "wireguard" in pkt.get("layers", [])
            or pkt.get("src_port") == 41641
            or pkt.get("dst_port") == 41641
        )
    if kw in ("http", "http2", "airpc", "ai-rpc", "sse"):
        return lambda pkt: (
            pkt.get("protocol") in ("HTTP", "HTTP/2", "AI-RPC", "AI-SSE")
            or "airpc" in pkt.get("layers", [])
            or "http" in pkt.get("layers", [])
            or pkt.get("src_port") in (8081, 8082, 8083, 8084)
            or pkt.get("dst_port") in (8081, 8082, 8083, 8084)
        )
    if kw == "tcp":
        return lambda pkt: (
            pkt.get("protocol") in ("TCP", "HTTP", "HTTP/2", "AI-RPC", "AI-SSE", "SSH")
            or "tcp" in pkt.get("layers", [])
        )
    if kw == "udp":
        return lambda pkt: (
            pkt.get("protocol") in ("UDP", "WireGuard", "DNS")
            or "udp" in pkt.get("layers", [])
        )
    if kw == "ssh":
        return lambda pkt: (
            pkt.get("protocol") == "SSH"
            or "ssh" in pkt.get("layers", [])
            or pkt.get("src_port") in (22, 8022)
            or pkt.get("dst_port") in (22, 8022)
        )
    if kw == "dns":
        return lambda pkt: (
            pkt.get("protocol") == "DNS"
            or "dns" in pkt.get("layers", [])
            or pkt.get("src_port") == 53
            or pkt.get("dst_port") == 53
        )
    if kw == "icmp":
        return lambda pkt: (
            pkt.get("protocol") == "ICMP"
            or "icmp" in pkt.get("layers", [])
        )
    if kw in ("ipv4", "ip"):
        return lambda pkt: "ipv4" in pkt.get("layers", [])
    if kw in ("ipv6", "ip6"):
        return lambda pkt: "ipv6" in pkt.get("layers", [])
    if kw in ("eth", "ethernet"):
        return lambda pkt: "eth" in pkt.get("layers", [])

    return lambda pkt: pkt.get("protocol", "").lower() == kw or kw in [str(l).lower() for l in pkt.get("layers", [])]


def _make_field_presence_matcher(field: str) -> Callable[[Dict[str, Any]], bool]:
    f = field.lower()
    return lambda pkt: bool(pkt.get(f) or pkt.get(f.replace(".", "_")))


def _make_comparison_matcher(field: str, op: str, value: Any) -> Callable[[Dict[str, Any]], bool]:
    f = field.lower()

    # Pre-parse integer value if applicable
    int_val: Optional[int] = None
    try:
        int_val = int(value)
    except (ValueError, TypeError):
        pass

    str_val = str(value).lower()

    # 1. IP Address Matching (ip.addr, ip.src, ip.dst)
    if f in ("ip.addr", "ip"):
        if op in ("==", "="):
            return lambda pkt: (
                pkt.get("src_ip") == value
                or pkt.get("dst_ip") == value
                or str(pkt.get("source", "")).split(":")[0] == value
                or str(pkt.get("destination", "")).split(":")[0] == value
            )
        if op == "!=":
            return lambda pkt: (
                pkt.get("src_ip") != value
                and pkt.get("dst_ip") != value
                and str(pkt.get("source", "")).split(":")[0] != value
                and str(pkt.get("destination", "")).split(":")[0] != value
            )
        if op == "contains":
            return lambda pkt: (
                value in str(pkt.get("src_ip", ""))
                or value in str(pkt.get("dst_ip", ""))
                or value in str(pkt.get("source", ""))
                or value in str(pkt.get("destination", ""))
            )

    if f in ("ip.src", "src_ip"):
        if op in ("==", "="):
            return lambda pkt: pkt.get("src_ip") == value or str(pkt.get("source", "")).split(":")[0] == value
        if op == "!=":
            return lambda pkt: pkt.get("src_ip") != value and str(pkt.get("source", "")).split(":")[0] != value

    if f in ("ip.dst", "dst_ip"):
        if op in ("==", "="):
            return lambda pkt: pkt.get("dst_ip") == value or str(pkt.get("destination", "")).split(":")[0] == value
        if op == "!=":
            return lambda pkt: pkt.get("dst_ip") != value and str(pkt.get("destination", "")).split(":")[0] != value

    # 2. Port Matching (port, tcp.port, udp.port)
    if f == "port" and int_val is not None:
        if op in ("==", "="):
            return lambda pkt: pkt.get("src_port") == int_val or pkt.get("dst_port") == int_val
        if op == "!=":
            return lambda pkt: pkt.get("src_port") != int_val and pkt.get("dst_port") != int_val

    if f in ("tcp.port", "tcp_port") and int_val is not None:
        if op in ("==", "="):
            return lambda pkt: (
                ("tcp" in pkt.get("layers", []) or pkt.get("protocol") in ("TCP", "AI-RPC", "AI-SSE", "HTTP", "SSH"))
                and (pkt.get("src_port") == int_val or pkt.get("dst_port") == int_val)
            )
        if op == "!=":
            return lambda pkt: (
                pkt.get("src_port") != int_val and pkt.get("dst_port") != int_val
            )

    if f in ("udp.port", "udp_port") and int_val is not None:
        if op in ("==", "="):
            return lambda pkt: (
                ("udp" in pkt.get("layers", []) or pkt.get("protocol") in ("UDP", "WireGuard", "DNS"))
                and (pkt.get("src_port") == int_val or pkt.get("dst_port") == int_val)
            )
        if op == "!=":
            return lambda pkt: (
                pkt.get("src_port") != int_val and pkt.get("dst_port") != int_val
            )

    # 3. Protocol Matching
    if f == "protocol":
        if op in ("==", "="):
            return lambda pkt: pkt.get("protocol", "").lower() == str_val
        if op == "!=":
            return lambda pkt: pkt.get("protocol", "").lower() != str_val
        if op == "contains":
            return lambda pkt: str_val in pkt.get("protocol", "").lower()

    # 4. Length Matching (len, length)
    if f in ("len", "length", "frame.len") and int_val is not None:
        if op in ("==", "="):
            return lambda pkt: pkt.get("length", 0) == int_val
        if op == "!=":
            return lambda pkt: pkt.get("length", 0) != int_val
        if op == ">":
            return lambda pkt: pkt.get("length", 0) > int_val
        if op == ">=":
            return lambda pkt: pkt.get("length", 0) >= int_val
        if op == "<":
            return lambda pkt: pkt.get("length", 0) < int_val
        if op == "<=":
            return lambda pkt: pkt.get("length", 0) <= int_val

    # 5. HTTP Method
    if f in ("http.method", "method"):
        if op in ("==", "="):
            return lambda pkt: str(pkt.get("http_method", "")).upper() == str_val.upper()
        if op == "!=":
            return lambda pkt: str(pkt.get("http_method", "")).upper() != str_val.upper()

    # 6. TCP SYN Flag
    if f in ("tcp.flags.syn", "syn"):
        target_flag = 1 if int_val == 1 or str_val in ("1", "true") else 0
        if op in ("==", "="):
            return lambda pkt: pkt.get("tcp_flags_syn", 0) == target_flag
        if op == "!=":
            return lambda pkt: pkt.get("tcp_flags_syn", 0) != target_flag

    # Generic Fallback Field Matcher
    key = f.replace(".", "_")
    if op in ("==", "="):
        return lambda pkt: str(pkt.get(key, pkt.get(f, ""))).lower() == str_val
    if op == "!=":
        return lambda pkt: str(pkt.get(key, pkt.get(f, ""))).lower() != str_val
    if op == "contains":
        return lambda pkt: str_val in str(pkt.get(key, pkt.get(f, ""))).lower()

    return lambda pkt: False
