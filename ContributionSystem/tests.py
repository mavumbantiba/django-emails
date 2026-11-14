# from django.test import TestCase
# from django.contrib.auth import get_user_model


# class UserModelTests(TestCase):
#     def test_create_user_with_school_profile(self):
#         user_model = get_user_model()
#         user = user_model.objects.create_user(
#             email="student@example.com",
#             password="secure-test-password",
#             phone="+256700000000",
#             role=user_model.Role.STUDENT,
#         )

#         self.assertEqual(user.email, "student@example.com")
#         self.assertEqual(user.phone, "+256700000000")
#         self.assertEqual(user.role, user_model.Role.STUDENT)
#         self.assertTrue(user.check_password("secure-test-password"))
#         self.assertFalse(user.is_staff)

#     def test_create_superuser_sets_required_permissions(self):
#         user = get_user_model().objects.create_superuser(
#             email="admin@example.com",
#             password="secure-test-password",
#         )

#         self.assertTrue(user.is_staff)
#         self.assertTrue(user.is_superuser)
