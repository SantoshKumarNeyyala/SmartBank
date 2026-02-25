from flask import request


def get_request_meta():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "")[:255]
    return ip, ua