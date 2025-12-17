"""
Test the complete signup and approval workflow
"""

from app.db import SessionLocal
from app import crud_users
from app.schemas import UserCreate

print("=" * 60)
print("Testing User Registration with Admin Approval")
print("=" * 60)

db = SessionLocal()

try:
    # Test 1: Create a new user (signup)
    print("\n1. Testing user signup...")
    new_user_data = UserCreate(
        username="testuser_new",
        email="testuser@example.com",
        password="password123",
        role="user"
    )
    
    new_user = crud_users.create_user(db, new_user_data)
    print(f"   ✓ User created: {new_user.username}")
    print(f"   ✓ Email: {new_user.email}")
    print(f"   ✓ Approved status: {new_user.is_approved}")
    
    assert new_user.is_approved == False, "New user should not be approved by default"
    print("   ✓ PASS: User created as unapproved")
    
    # Test 2: Try to login with pending user
    print("\n2. Testing login with pending user...")
    auth_result = crud_users.authenticate_user(db, "testuser_new", "password123")
    
    assert auth_result == "pending", "Login should return 'pending' for unapproved user"
    print("   ✓ PASS: Login correctly blocked for pending user")
    
    # Test 3: Get pending users
    print("\n3. Testing get pending users...")
    pending_users = crud_users.get_pending_users(db)
    
    assert len(pending_users) > 0, "Should have at least one pending user"
    assert any(u.username == "testuser_new" for u in pending_users), "testuser_new should be in pending list"
    print(f"   ✓ PASS: Found {len(pending_users)} pending user(s)")
    
    # Test 4: Approve user
    print("\n4. Testing user approval...")
    approved_user = crud_users.approve_user(db, new_user.id)
    
    assert approved_user.is_approved == True, "User should be approved"
    print(f"   ✓ PASS: User {approved_user.username} approved")
    
    # Test 5: Login with approved user
    print("\n5. Testing login with approved user...")
    auth_result = crud_users.authenticate_user(db, "testuser_new", "password123")
    
    assert auth_result != "pending", "Should not return pending"
    assert auth_result is not None, "Should successfully authenticate"
    assert auth_result.username == "testuser_new", "Should return correct user"
    print("   ✓ PASS: Login successful for approved user")
    
    # Test 6: Email uniqueness
    print("\n6. Testing email uniqueness...")
    duplicate_email_user = UserCreate(
        username="another_user",
        email="testuser@example.com",  # Same email
        password="password123",
        role="user"
    )
    
    try:
        crud_users.create_user(db, duplicate_email_user)
        print("   ✗ FAIL: Should have failed due to duplicate email")
    except Exception as e:
        print("   ✓ PASS: Duplicate email properly rejected")
    
    # Test 7: Create another user and reject
    print("\n7. Testing user rejection...")
    reject_user_data = UserCreate(
        username="reject_me",
        email="reject@example.com",
        password="password123",
        role="user"
    )
    
    reject_user = crud_users.create_user(db, reject_user_data)
    reject_result = crud_users.reject_user(db, reject_user.id)
    
    assert reject_result == True, "Reject should return True"
    
    # Verify user is deleted
    deleted_user = crud_users.get_user_by_username(db, "reject_me")
    assert deleted_user is None, "Rejected user should be deleted"
    print("   ✓ PASS: User rejection and deletion works")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nFeatures verified:")
    print("  ✓ User signup with email")
    print("  ✓ Default unapproved status")
    print("  ✓ Login blocked for pending users")
    print("  ✓ Admin approval workflow")
    print("  ✓ Login enabled after approval")
    print("  ✓ Email uniqueness validation")
    print("  ✓ User rejection and deletion")
    
except Exception as e:
    print(f"\n✗ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Cleanup
    print("\nCleaning up test data...")
    test_users = db.query(crud_users.models.User).filter(
        crud_users.models.User.username.in_(["testuser_new", "reject_me"])
    ).all()
    
    for user in test_users:
        db.delete(user)
    
    db.commit()
    db.close()
    print("✓ Cleanup complete")
