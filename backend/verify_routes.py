#!/usr/bin/env python3
"""Verify FastAPI router registration and list all routes."""

from collections import Counter

from app.main import app


def list_all_routes() -> None:
    """List all registered routes and verify critical endpoints."""
    routes = []
    route_details = []

    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            path = route.path
            methods = list(route.methods) if route.methods else []
            # Filter out HEAD and OPTIONS (auto-added by FastAPI)
            methods = [m for m in methods if m not in ("HEAD", "OPTIONS")]
            
            if methods:  # Only include routes with actual HTTP methods
                routes.append(path)
                route_details.append({
                    "path": path,
                    "methods": methods,
                    "name": getattr(route, "name", "N/A"),
                })

    # Sort for readability
    route_details.sort(key=lambda x: x["path"])

    print("=" * 80)
    print("FASTAPI ROUTER TABLE")
    print("=" * 80)
    print(f"\nTotal routes found: {len(routes)}\n")

    # Group by path to show all methods
    path_to_methods: dict[str, list[str]] = {}
    for detail in route_details:
        path = detail["path"]
        if path not in path_to_methods:
            path_to_methods[path] = []
        path_to_methods[path].extend(detail["methods"])

    for path in sorted(path_to_methods.keys()):
        methods = sorted(set(path_to_methods[path]))
        methods_str = ", ".join(methods)
        print(f"  {methods_str:20s}  {path}")

    print("\n" + "=" * 80)
    print("VERIFICATION: Critical System Endpoints")
    print("=" * 80)

    # Count occurrences
    route_counter = Counter(routes)
    
    critical_endpoints = [
        "/system/models",
        "/system/identity-guard/status",
    ]

    all_good = True
    for endpoint in critical_endpoints:
        count = route_counter[endpoint]
        status = "✅" if count == 1 else "❌"
        print(f"{status}  {endpoint:40s}  (appears {count} time{'s' if count != 1 else ''})")
        
        if count != 1:
            all_good = False
            if count == 0:
                print(f"     ERROR: Endpoint not found in router table!")
            elif count > 1:
                print(f"     WARNING: Endpoint registered {count} times (duplicate registration)")

    print("\n" + "=" * 80)
    if all_good:
        print("✅ VERIFICATION PASSED: All critical endpoints registered exactly once")
    else:
        print("❌ VERIFICATION FAILED: Some endpoints have issues")
    print("=" * 80)

    return all_good


if __name__ == "__main__":
    import sys
    success = list_all_routes()
    sys.exit(0 if success else 1)

