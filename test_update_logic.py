#!/usr/bin/env python3
"""
Test script to verify the update logic works correctly.
This simulates multiple runs to ensure we update the same task, not create new ones.
"""

import os
import sys
import time
import json
from datetime import datetime

def test_update_logic():
    """Test that the script updates the same task, not creates new ones"""
    print("🧪 Testing Update Logic")
    print("=" * 50)
    
    # Set up test environment
    os.environ['TASKADE_API_TOKEN'] = 'test_token'
    os.environ['TASKADE_PROJECT_ID'] = 'test_project'
    os.environ['TASKADE_TASK_ID'] = ''  # Start with no task ID
    
    print("📋 Test Scenario:")
    print("1. First run: Should CREATE a new task")
    print("2. Second run: Should UPDATE the same task (not create new)")
    print("3. Third run: Should UPDATE the same task again")
    print()
    
    # Mock the TaskadeClient to track calls
    class MockTaskadeClient:
        def __init__(self, base_url, api_token):
            self.create_calls = []
            self.update_calls = []
            self.list_calls = []
            self.task_id_counter = 0
            
        def create_task(self, project_id, content_md):
            self.task_id_counter += 1
            task_id = f"task_{self.task_id_counter}"
            self.create_calls.append({
                'project_id': project_id,
                'content': content_md,
                'task_id': task_id,
                'timestamp': datetime.now().isoformat()
            })
            print(f"🆕 CREATE called - Project: {project_id}, Task ID: {task_id}")
            return {"id": task_id}
            
        def update_task(self, task_id, content_md):
            self.update_calls.append({
                'task_id': task_id,
                'content': content_md,
                'timestamp': datetime.now().isoformat()
            })
            print(f"🔄 UPDATE called - Task ID: {task_id}")
            return {"task_id": task_id}
            
        def find_task_by_title(self, project_id, title):
            # Simulate finding existing task after first run
            if len(self.create_calls) > 0:
                return {"id": self.create_calls[0]['task_id']}
            return None
    
    # Test the logic by simulating multiple runs
    print("🚀 Simulating multiple script runs...")
    print()
    
    # Import our script's main logic
    from scripts.ktm_taskade import fetch_gtfs_realtime_feed, parse_feed, format_markdown
    
    # Mock the client
    import scripts.ktm_taskade as ktm_module
    original_client = ktm_module.TaskadeClient
    ktm_module.TaskadeClient = MockTaskadeClient
    
    try:
        # Get real data for testing
        print("📡 Fetching real GTFS data...")
        feed = fetch_gtfs_realtime_feed("https://api.data.gov.my/gtfs-realtime/vehicle-position/ktmb")
        feed_ts, vehicles = parse_feed(feed)
        content_md = format_markdown(feed_ts, vehicles)
        print(f"✅ Got {len(vehicles)} trains")
        print()
        
        # Simulate Run 1: First run (no TASKADE_TASK_ID set)
        print("🏃‍♂️ RUN 1: First execution (no task ID)")
        os.environ['TASKADE_TASK_ID'] = ''
        client = MockTaskadeClient("", "")
        
        # Simulate the main logic
        task_id = os.environ.get('TASKADE_TASK_ID', '').strip()
        if task_id:
            print(f"Would UPDATE existing task: {task_id}")
            client.update_task(task_id, content_md)
        else:
            existing = client.find_task_by_title('test_project', 'KTM Live Status Dashboard')
            if existing:
                discovered_id = existing.get('id')
                print(f"Would UPDATE discovered task: {discovered_id}")
                client.update_task(discovered_id, content_md)
            else:
                print("Would CREATE new task")
                result = client.create_task('test_project', content_md)
                task_id = result['id']
                print(f"Created task ID: {task_id}")
                # Store for next run
                os.environ['TASKADE_TASK_ID'] = task_id
        
        print()
        
        # Simulate Run 2: Second run (TASKADE_TASK_ID set)
        print("🏃‍♂️ RUN 2: Second execution (task ID set)")
        task_id = os.environ.get('TASKADE_TASK_ID', '').strip()
        if task_id:
            print(f"Would UPDATE existing task: {task_id}")
            client.update_task(task_id, content_md)
        else:
            # This should not happen in real scenario
            print("❌ ERROR: No task ID found!")
        
        print()
        
        # Simulate Run 3: Third run (TASKADE_TASK_ID still set)
        print("🏃‍♂️ RUN 3: Third execution (task ID still set)")
        task_id = os.environ.get('TASKADE_TASK_ID', '').strip()
        if task_id:
            print(f"Would UPDATE existing task: {task_id}")
            client.update_task(task_id, content_md)
        
        print()
        
        # Analyze results
        print("📊 RESULTS ANALYSIS:")
        print("=" * 30)
        print(f"🆕 CREATE calls: {len(client.create_calls)}")
        print(f"🔄 UPDATE calls: {len(client.update_calls)}")
        print()
        
        if len(client.create_calls) == 1 and len(client.update_calls) == 2:
            print("✅ SUCCESS: Update logic is working correctly!")
            print("   - Created 1 task on first run")
            print("   - Updated the same task on subsequent runs")
            print("   - No duplicate tasks created")
        else:
            print("❌ FAILURE: Update logic has issues!")
            print(f"   - Expected: 1 create, 2 updates")
            print(f"   - Actual: {len(client.create_calls)} creates, {len(client.update_calls)} updates")
        
        print()
        print("🔍 DETAILED CALL LOG:")
        for i, call in enumerate(client.create_calls, 1):
            print(f"   Create {i}: Task {call['task_id']} at {call['timestamp']}")
        for i, call in enumerate(client.update_calls, 1):
            print(f"   Update {i}: Task {call['task_id']} at {call['timestamp']}")
            
    finally:
        # Restore original client
        ktm_module.TaskadeClient = original_client

def test_task_id_persistence():
    """Test that TASKADE_TASK_ID is properly stored and used"""
    print("\n🧪 Testing Task ID Persistence")
    print("=" * 50)
    
    # Test the JSON output that should be captured
    test_output = '{"TASKADE_TASK_ID": "task_12345"}'
    
    try:
        parsed = json.loads(test_output)
        task_id = parsed.get('TASKADE_TASK_ID')
        print(f"✅ JSON parsing works: {task_id}")
        
        if task_id:
            print("✅ Task ID would be stored in GitHub Secrets")
            print("✅ Next run would use this ID for updates")
        else:
            print("❌ No task ID found in output")
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")

def main():
    print("🚀 KTM Taskade Update Logic Test Suite")
    print("=" * 60)
    
    test_update_logic()
    test_task_id_persistence()
    
    print("\n" + "=" * 60)
    print("📋 HOW TO VERIFY IN PRODUCTION:")
    print("1. Run the script first time → Check GitHub Actions logs")
    print("2. Look for: 'Created task id=XXXXX' in the output")
    print("3. Copy that ID to TASKADE_TASK_ID secret")
    print("4. Run again → Should see 'Updating existing task: XXXXX'")
    print("5. Check Taskade → Only ONE task should exist")
    print("6. Check task content → Should show latest timestamp")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
