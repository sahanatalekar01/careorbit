from app import app

# Create Flask test client
client = app.test_client()

def test_all_routes():
    # Find all GET routes that don't require URL parameters (like <int:id>)
    endpoints = []
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and not rule.arguments:
            endpoints.append((rule.endpoint, rule.rule))

    print(f"\n Testing {len(endpoints)} routes...\n" + "="*45)
    
    passed = 0
    failed = 0

    for endpoint, url in endpoints:
        try:
            # Request the route to trigger Jinja rendering & url_for checks
            response = client.get(url, follow_redirects=True)
            if response.status_code in [200, 302]:
                print(f" [OK {response.status_code}] {endpoint:30} -> {url}")
                passed += 1
            else:
                print(f" [HTTP {response.status_code}] {endpoint:30} -> {url}")
                failed += 1
        except Exception as e:
            print(f" [FAILED] {endpoint:30} -> {url}\n   Error: {e}\n")
            failed += 1

    print("="*45)
    print(f"Summary: {passed} Passed | {failed} Failed\n")

if __name__ == "__main__":
    test_all_routes()