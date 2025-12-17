"""
Quick test for update_user_credentials functionality
"""

from app.db import SessionLocal
from app import crud_users
from app.schemas import UserCreate

# Create database session
db = SessionLocal()

try:
    # First, create a test user if needed
    print("Setting up test user...")
    test_user = crud_users.get_user_by_username(db, "testuser")
    if not test_user:
        user_data = UserCreate(username="testuser", password="password123", role="user")
        test_user = crud_users.create_user(db, user_data)
        print(f"✓ Created test user: {test_user.username} (ID: {test_user.id})")
    else:
        print(f"✓ Test user exists: {test_user.username} (ID: {test_user.id})")
    
    print()
    
    # Test 1: Update username
    print("Test 1: Updating username...")
    updated_user = crud_users.update_user_credentials(
        db=db,
        user_id=test_user.id,
        new_username="testuser_updated"
    )
    assert updated_user is not None, "User should be found"
    assert updated_user.username == "testuser_updated", "Username should be updated"
    print(f"✓ PASS: Username updated to '{updated_user.username}'")
    
    print()
    
    # Test 2: Update password
    print("Test 2: Updating password...")
    old_hash = updated_user.hashed_password
    updated_user = crud_users.update_user_credentials(
        db=db,
        user_id=updated_user.id,
        new_password="newpassword456"
    )
    assert updated_user.hashed_password != old_hash, "Password hash should change"
    # Verify we can authenticate with new password
    auth_user = crud_users.authenticate_user(db, "testuser_updated", "newpassword456")
    assert auth_user is not None, "Authentication should succeed with new password"
    print("✓ PASS: Password updated and authentication works")
    
    print()
    
    # Test 3: Update both
    print("Test 3: Updating both username and password...")
    updated_user = crud_users.update_user_credentials(
        db=db,
        user_id=updated_user.id,
        new_username="final_username",
        new_password="finalpass789"
    )
    assert updated_user.username == "final_username", "Username should be updated"
    auth_user = crud_users.authenticate_user(db, "final_username", "finalpass789")
    assert auth_user is not None, "Authentication should work with both new credentials"
    print("✓ PASS: Both credentials updated successfully")
    
    print()
    
    # Test 4: Duplicate username error
    print("Test 4: Testing duplicate username validation...")
    # Create another user
    user2_data = UserCreate(username="anotheruser", password="pass123", role="user")
    user2 = crud_users.create_user(db, user2_data)
    
    try:
        crud_users.update_user_credentials(
            db=db,
            user_id=user2.id,
            new_username="final_username"  # Already exists
        )
        print("✗ FAIL: Should have raised ValueError")
    except ValueError as e:
        print(f"✓ PASS: Correctly raised ValueError: {e}")
    
    print()
    print("=" * 50)
    print("ALL TESTS PASSED! ✓")
    print("=" * 50)

except Exception as e:
    print(f"✗ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Cleanup
    db.query(crud_users.models.User).filter(
        crud_users.models.User.username.in_(["testuser", "testuser_updated", "final_username", "anotheruser"])
    ).delete(synchronize_session=False)
    db.commit()
    db.close()
    print("\nCleanup completed.")
