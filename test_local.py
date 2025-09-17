#!/usr/bin/env python3
"""
Local test script for KTM Taskade integration.
Run this to test the script before deploying to GitHub Actions.
"""

import os
import sys
import subprocess
from pathlib import Path

def test_gtfs_fetch():
    """Test GTFS-R data fetching without Taskade integration"""
    print("🧪 Testing GTFS-R data fetch...")
    
    try:
        # Test just the GTFS parsing part
        from scripts.ktm_taskade import fetch_gtfs_realtime_feed, parse_feed, format_markdown
        
        feed = fetch_gtfs_realtime_feed("https://api.data.gov.my/gtfs-realtime/vehicle-position/ktmb")
        feed_ts, vehicles = parse_feed(feed)
        content_md = format_markdown(feed_ts, vehicles)
        
        print(f"✅ GTFS-R fetch successful!")
        print(f"📊 Found {len(vehicles)} trains")
        print(f"📝 Content preview (first 500 chars):")
        print("-" * 50)
        print(content_md[:500] + "..." if len(content_md) > 500 else content_md)
        print("-" * 50)
        return True
        
    except Exception as e:
        print(f"❌ GTFS-R test failed: {e}")
        return False

def test_with_mock_taskade():
    """Test with mock Taskade API (dry run)"""
    print("\n🧪 Testing with mock Taskade API...")
    
    # Set mock environment variables
    os.environ['TASKADE_API_TOKEN'] = 'mock_token_for_testing'
    os.environ['TASKADE_PROJECT_ID'] = 'mock_project_123'
    os.environ['TASKADE_TASK_ID'] = ''  # Will trigger create flow
    
    try:
        from scripts.ktm_taskade import main
        
        # This will fail at the API call, but we can see if parsing works
        result = main()
        print(f"✅ Mock test completed with exit code: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Mock test failed: {e}")
        return False

def test_dependencies():
    """Test if all required dependencies are installed"""
    print("🧪 Testing dependencies...")
    
    # Test specific imports that our script uses
    import_tests = [
        ('requests', 'requests'),
        ('gtfs-realtime-bindings', 'google.transit.gtfs_realtime_pb2'),
        ('pytz', 'pytz')
    ]
    
    missing_packages = []
    
    for package_name, import_name in import_tests:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - MISSING")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n📦 Install missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All dependencies installed!")
    return True

def main():
    print("🚀 KTM Taskade Local Test Suite")
    print("=" * 50)
    
    # Test 1: Dependencies
    deps_ok = test_dependencies()
    if not deps_ok:
        print("\n❌ Please install missing dependencies first")
        return 1
    
    # Test 2: GTFS-R fetch
    gtfs_ok = test_gtfs_fetch()
    if not gtfs_ok:
        print("\n❌ GTFS-R fetch failed")
        return 1
    
    # Test 3: Mock Taskade (optional)
    print("\n" + "=" * 50)
    print("🎯 Ready for real testing!")
    print("\nTo test with real Taskade API:")
    print("1. Set environment variables:")
    print("   export TASKADE_API_TOKEN='your_token_here'")
    print("   export TASKADE_PROJECT_ID='your_project_id_here'")
    print("2. Run: python scripts/ktm_taskade.py")
    print("\nOr run the GitHub Action workflow manually!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
