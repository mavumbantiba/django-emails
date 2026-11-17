from datetime import timedelta

from allauth.mfa.models import Authenticator
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase

from ContributionSystem.models import Parent, Student

from .models import Book, BookLoan


class LibraryManagementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="library-staff",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(self.user)
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.TOTP,
            data={"secret": "test-secret"},
        )
        parent = Parent.objects.create(
            full_name="Library Parent",
            phone_number="0700000000",
        )
        self.student = Student.objects.create(
            admission_number="LIB-001",
            first_name="Amina",
            last_name="Mushi",
            gender=Student.Gender.FEMALE,
            class_level="Form One",
            parent=parent,
            ward="Town",
            village="Village",
            street="Main Road",
        )
        self.book = Book.objects.create(
            title="The School Reader",
            author="A. Writer",
            total_copies=1,
        )

    def test_library_requires_staff_access(self):
        response = self.client.get(reverse("library:dashboard"))
        self.assertEqual(response.status_code, 200)
        homepage = self.client.get(reverse("home"))
        self.assertContains(homepage, reverse("library:dashboard"))
        self.assertContains(homepage, "Open the library")

        regular_user = get_user_model().objects.create_user(
            username="library-student",
            password="test-password",
        )
        Authenticator.objects.create(
            user=regular_user,
            type=Authenticator.Type.TOTP,
            data={"secret": "test-secret"},
        )
        self.client.force_login(regular_user)

        response = self.client.get(reverse("library:dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_issue_and_return_updates_copy_availability(self):
        issue_response = self.client.post(
            reverse("library:loan-create"),
            {
                "book": self.book.pk,
                "student": self.student.pk,
                "book_number": "01/100",
                "due_date": (timezone.localdate() + timedelta(days=14)).isoformat(),
            },
        )

        self.assertRedirects(issue_response, reverse("library:loan-list"))
        loan = BookLoan.objects.get(book=self.book, student=self.student)
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 0)
        self.assertEqual(loan.issued_by, self.user)
        self.assertEqual(loan.book_number, "01/100")

        return_response = self.client.post(
            reverse("library:loan-return", args=[loan.pk]),
            {"book_number": "01/100"},
        )

        self.assertRedirects(return_response, reverse("library:loan-list"))
        loan.refresh_from_db()
        self.book.refresh_from_db()
        self.assertIsNotNone(loan.returned_at)
        self.assertEqual(self.book.available_copies, 1)

    def test_return_requires_the_issued_copy_number(self):
        loan = BookLoan.objects.create(
            book=self.book,
            student=self.student,
            book_number="01/100",
            issued_by=self.user,
            due_date=timezone.localdate() + timedelta(days=14),
        )

        response = self.client.post(
            reverse("library:loan-return", args=[loan.pk]),
            {"book_number": "02/100"},
        )

        self.assertRedirects(response, reverse("library:loan-list"))
        loan.refresh_from_db()
        self.assertIsNone(loan.returned_at)
        self.assertContains(
            self.client.get(reverse("library:loan-list")),
            "still active",
        )

    def test_same_book_number_cannot_be_issued_twice_at_once(self):
        self.book.total_copies = 2
        self.book.save(update_fields=["total_copies"])
        BookLoan.objects.create(
            book=self.book,
            student=self.student,
            book_number="01/100",
            issued_by=self.user,
            due_date=timezone.localdate() + timedelta(days=14),
        )
        other_student = Student.objects.create(
            admission_number="LIB-003",
            first_name="Daniel",
            last_name="Mushi",
            gender=Student.Gender.MALE,
            class_level="Form Two",
            parent=self.student.parent,
            ward="Town",
            village="Village",
            street="Main Road",
        )

        response = self.client.post(
            reverse("library:loan-create"),
            {
                "book": self.book.pk,
                "student": other_student.pk,
                "book_number": "01/100",
                "due_date": (timezone.localdate() + timedelta(days=14)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already on an active loan")
        self.assertEqual(BookLoan.objects.filter(book=self.book).count(), 1)

    def test_library_pages_render_and_book_can_be_added(self):
        dashboard = self.client.get(reverse("library:dashboard"))
        self.assertContains(dashboard, 'id="theme-toggle"')
        self.assertContains(dashboard, "static/js/ui-feedback.js")

        for route_name in (
            "library:dashboard",
            "library:book-create",
            "library:loan-list",
            "library:loan-create",
        ):
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                if route_name == "library:loan-create":
                    self.assertContains(response, 'name="book_number"')

        response = self.client.post(
            reverse("library:book-create"),
            {
                "title": "A New Library Book",
                "author": "A. Author",
                "isbn": "",
                "category": Book.Category.REFERENCE,
                "publisher": "",
                "publication_year": "",
                "shelf_location": "A-02",
                "total_copies": 3,
                "description": "",
            },
        )

        self.assertRedirects(response, reverse("library:dashboard"))
        self.assertTrue(
            Book.objects.filter(
                title="A New Library Book",
                isbn__isnull=True,
                total_copies=3,
            ).exists()
        )

    def test_unavailable_copy_cannot_be_issued(self):
        BookLoan.objects.create(
            book=self.book,
            student=self.student,
            book_number="01/100",
            issued_by=self.user,
            due_date=timezone.localdate() + timedelta(days=14),
        )
        parent = self.student.parent
        other_student = Student.objects.create(
            admission_number="LIB-002",
            first_name="Daniel",
            last_name="Mushi",
            gender=Student.Gender.MALE,
            class_level="Form Two",
            parent=parent,
            ward="Town",
            village="Village",
            street="Main Road",
        )

        response = self.client.post(
            reverse("library:loan-create"),
            {
                "book": self.book.pk,
                "student": other_student.pk,
                "due_date": (timezone.localdate() + timedelta(days=14)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BookLoan.objects.filter(book=self.book).count(), 1)
