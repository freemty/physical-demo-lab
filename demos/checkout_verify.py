"""Checkout business predicates layered on independently measured physics."""
from verification import verify_object


def verify_checkout(states, bag, inventory, scans):
    items = [verify_object(state, bag) for state in states]
    expected = {item['id']: item['price_cents'] for item in inventory}
    ids = [scan['id'] for scan in scans]
    checks = {
        'all_items_physically_bagged': len(items) == len(expected) and all(item['success'] for item in items),
        'all_unique_skus_scanned': len(ids) == len(expected) and set(ids) == set(expected) and len(set(ids)) == len(ids),
        'scan_volume_observed': all(scan.get('dwell_frames', 0) >= 12 and scan.get('inside_volume') is True for scan in scans),
        'correct_line_prices': all(scan.get('price_cents') == expected.get(scan['id']) for scan in scans),
        'correct_total': sum(scan.get('price_cents', 0) for scan in scans) == sum(expected.values()),
    }
    return {'success': all(checks.values()), 'checks': checks, 'items': items}
