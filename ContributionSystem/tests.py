import time
from html.parser import HTMLParser
from smtplib import SMTPException
from unittest.mock import patch

from allauth.account.internal.flows.login import AUTHENTICATION_METHODS_SESSION_KEY
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core import mail
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from .access import (
    ACCOUNTANT_ROLE,
    ACADEMIC_ROLE,
    SECOND_HEAD_ROLE,
)
from .adapters import SchoolAccountAdapter
from .models import (
    AccountRecoveryRequest,
    Parent,
    Student,
    StudentClothingVerification,
    StudentCollection,
    StoreSupplyReceipt,
)


def login_with_totp(client, user, recently_authenticated=True, roles=None):
    if roles is None and not user.is_superuser:
        user.is_superuser = True
        user.is_staff = True
        user.save(update_fields=["is_superuser", "is_staff"])
    elif roles:
        user.groups.add(*Group.objects.filter(name__in=roles))
    client.force_login(user)
    Authenticator.objects.create(
        user=user,
        type=Authenticator.Type.TOTP,
        data={"secret": "test-secret"},
    )
    if recently_authenticated:
        session = client.session
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {"method": "mfa", "type": "totp", "at": time.time()}
        ]
        session.save()


class ScriptNonceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script_attributes = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.script_attributes.append(dict(attrs))


class HtmxListSearchTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="school-staff",
            password="test-password",
        )
        login_with_totp(self.client, user)
        self.parent = Parent.objects.create(
            full_name="Amina Mwinyi",
            phone_number="0712345678",
        )
        self.other_parent = Parent.objects.create(
            full_name="Juma Baraka",
            phone_number="0798765432",
        )
        self.student = Student.objects.create(
            admission_number="KSS-001",
            first_name="Neema",
            last_name="Amina",
            gender=Student.Gender.FEMALE,
            class_level="Form One",
            parent=self.parent,
            ward="Kayanga",
            village="Town",
            street="Main Road",
        )
        Student.objects.create(
            admission_number="KSS-002",
            first_name="Baraka",
            last_name="Juma",
            gender=Student.Gender.MALE,
            class_level="Form Two",
            parent=self.other_parent,
            ward="Bugene",
            village="Centre",
            street="School Road",
        )
        StudentCollection.objects.create(
            student=self.student,
            category=StudentCollection.Category.ACADEMIC_FEE,
            amount_collected="25000.00",
        )
        StudentCollection.objects.create(
            student=self.student,
            category=StudentCollection.Category.TSHIRT,
            quantity_issued=1,
        )

    def test_parent_htmx_search_returns_matching_partial(self):
        response = self.client.get(
            reverse("parent-list"),
            {"q": "Amina"},
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, "Amina Mwinyi")
        self.assertNotContains(response, "Juma Baraka")
        self.assertNotContains(response, "<html")
        self.assertIn("HX-Request", response.headers.get("Vary", ""))

    def test_student_search_matches_parent_and_keeps_regular_page_fallback(self):
        response = self.client.get(
            reverse("student-list"),
            {"q": "Amina Mwinyi"},
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, "KSS-001")
        self.assertNotContains(response, "KSS-002")
        self.assertNotContains(response, "<html")

        full_page = self.client.get(reverse("student-list"), {"q": "KSS-001"})
        self.assertContains(full_page, "<html")
        self.assertContains(full_page, "KSS-001")
        self.assertNotContains(full_page, "KSS-002")

    def test_collection_htmx_search_matches_category(self):
        response = self.client.get(
            reverse("collection-list"),
            {"q": "academic_fee"},
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, "Academic fee")
        self.assertNotContains(response, "T-shirt")


class StudentRegistrationTemplateTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="registrar",
            password="test-password",
        )
        login_with_totp(self.client, user)

    def test_registration_form_groups_student_parent_and_address_fields(self):
        Parent.objects.create(full_name="Amina Mwinyi", phone_number="0712345678")

        response = self.client.get(reverse("student-create"))

        self.assertContains(response, "Student details")
        self.assertContains(response, "Parent or guardian")
        self.assertContains(response, "Physical address")
        self.assertContains(response, 'name="admission_number"')
        self.assertContains(response, 'name="parent"')
        self.assertContains(response, 'name="ward"')

    def test_registration_requires_parent_record_first(self):
        response = self.client.get(reverse("student-create"))

        self.assertContains(response, "Add a parent before registering this student")
        self.assertContains(response, "disabled")


class ParentAndCollectionFormTemplateTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="school-clerk",
            password="test-password",
        )
        login_with_totp(self.client, user)

    def test_parent_form_uses_shared_styled_fields(self):
        response = self.client.get(reverse("parent-create"))

        self.assertContains(response, "Parent contact details")
        self.assertContains(response, "name=\"full_name\"")
        self.assertContains(response, "name=\"phone_number\"")
        self.assertContains(response, "Save parent")

    def test_collection_form_requires_a_student_first(self):
        response = self.client.get(reverse("collection-create"))

        self.assertContains(response, "Register a student first")
        self.assertContains(response, "disabled")

    def test_collection_form_shows_entry_fields_when_students_exist(self):
        parent = Parent.objects.create(
            full_name="Amina Mwinyi",
            phone_number="0712345678",
        )
        Student.objects.create(
            admission_number="KSS-101",
            first_name="Neema",
            last_name="Amina",
            gender=Student.Gender.FEMALE,
            class_level="Form One",
            parent=parent,
            ward="Kayanga",
            village="Town",
            street="Main Road",
        )

        response = self.client.get(reverse("collection-create"))

        self.assertContains(response, "Collection details")
        self.assertContains(response, 'name="student"')
        self.assertContains(response, 'name="category"')
        self.assertContains(response, 'name="amount_collected"')
        self.assertContains(response, 'name="quantity_issued"')
        self.assertContains(response, "Save collection")


class StoreSupplyWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="storekeeper",
            password="test-password",
        )
        login_with_totp(self.client, self.user)
        parent = Parent.objects.create(
            full_name="Amina Mwinyi",
            phone_number="0712345678",
        )
        self.student = Student.objects.create(
            admission_number="KSS-SUPPLY-1",
            first_name="Neema",
            last_name="Amina",
            gender=Student.Gender.FEMALE,
            class_level="Form One",
            parent=parent,
            ward="Kayanga",
            village="Town",
            street="Main Road",
        )

    def test_storekeeper_can_record_a_supply_receipt(self):
        response = self.client.post(
            reverse("supply-create"),
            {
                "student": self.student.pk,
                "source": "Community donation",
                "notes": "",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "1",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-item": StoreSupplyReceipt.Item.HOE,
                "items-0-quantity_collected": "3",
            },
        )

        receipt = StoreSupplyReceipt.objects.get()
        self.assertRedirects(response, reverse("supply-list"))
        self.assertEqual(receipt.quantity_collected, 3)
        self.assertEqual(receipt.student, self.student)
        self.assertEqual(receipt.recorded_by, self.user)

    def test_storekeeper_can_record_multiple_items_with_individual_quantities(self):
        response = self.client.post(
            reverse("supply-create"),
            {
                "student": self.student.pk,
                "source": "Student submission",
                "notes": "First delivery",
                "items-TOTAL_FORMS": "2",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "1",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-item": StoreSupplyReceipt.Item.HOE,
                "items-0-quantity_collected": "2",
                "items-1-item": StoreSupplyReceipt.Item.BROOM,
                "items-1-quantity_collected": "5",
            },
        )

        receipts = list(StoreSupplyReceipt.objects.order_by("item"))
        self.assertRedirects(response, reverse("supply-list"))
        self.assertEqual(len(receipts), 2)
        self.assertEqual(
            {(receipt.item, receipt.quantity_collected) for receipt in receipts},
            {
                (StoreSupplyReceipt.Item.HOE, 2),
                (StoreSupplyReceipt.Item.BROOM, 5),
            },
        )
        self.assertTrue(all(receipt.student == self.student for receipt in receipts))
        self.assertTrue(all(receipt.recorded_by == self.user for receipt in receipts))
        self.assertTrue(all(receipt.source == "Student submission" for receipt in receipts))

    def test_invalid_item_quantity_prevents_saving_any_receipts(self):
        response = self.client.post(
            reverse("supply-create"),
            {
                "student": self.student.pk,
                "source": "",
                "notes": "",
                "items-TOTAL_FORMS": "2",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "1",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-item": StoreSupplyReceipt.Item.HOE,
                "items-0-quantity_collected": "2",
                "items-1-item": StoreSupplyReceipt.Item.BROOM,
                "items-1-quantity_collected": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(StoreSupplyReceipt.objects.exists())
        self.assertContains(
            response,
            "Ensure this value is greater than or equal to 1.",
        )

    def test_supply_receipt_requires_a_student(self):
        response = self.client.post(
            reverse("supply-create"),
            {
                "source": "",
                "notes": "",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "1",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-item": StoreSupplyReceipt.Item.HOE,
                "items-0-quantity_collected": "3",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(StoreSupplyReceipt.objects.exists())
        self.assertContains(response, "This field is required.")

    def test_supply_form_renders_add_item_controls(self):
        response = self.client.get(reverse("supply-create"))

        self.assertContains(response, 'name="items-0-item"')
        self.assertContains(response, 'name="items-0-quantity_collected"')
        self.assertContains(response, "Add another item")
        self.assertContains(response, "supply-items.js")

    def test_supply_form_requires_a_registered_student(self):
        self.student.delete()

        response = self.client.get(reverse("supply-create"))

        self.assertContains(response, "Register a student first")
        self.assertContains(response, "disabled")

    def test_supply_search_matches_english_item_label(self):
        StoreSupplyReceipt.objects.create(
            student=self.student,
            item=StoreSupplyReceipt.Item.TOILET_PAPER,
            quantity_collected=5,
            recorded_by=self.user,
        )
        StoreSupplyReceipt.objects.create(
            student=self.student,
            item=StoreSupplyReceipt.Item.BROOM,
            quantity_collected=2,
            recorded_by=self.user,
        )

        response = self.client.get(
            reverse("supply-list"),
            {"q": "Toilet paper"},
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, "Toilet paper")
        self.assertNotContains(response, "Broom")

    def test_supply_search_matches_student(self):
        StoreSupplyReceipt.objects.create(
            student=self.student,
            item=StoreSupplyReceipt.Item.HOE,
            quantity_collected=1,
        )

        response = self.client.get(
            reverse("supply-list"),
            {"q": "KSS-SUPPLY-1"},
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, "Hoe")
        self.assertContains(response, "Neema Amina")
        self.assertContains(response, "button-edit button-small")

    def test_student_supply_history_keeps_each_delivery_and_shows_totals(self):
        StoreSupplyReceipt.objects.create(
            student=self.student,
            item=StoreSupplyReceipt.Item.MACHETE,
            quantity_collected=2,
            source="First delivery",
        )
        StoreSupplyReceipt.objects.create(
            student=self.student,
            item=StoreSupplyReceipt.Item.MACHETE,
            quantity_collected=3,
            source="Later delivery",
        )
        other_parent = Parent.objects.create(
            full_name="Baraka Juma",
            phone_number="0700000000",
        )
        other_student = Student.objects.create(
            admission_number="KSS-SUPPLY-2",
            first_name="Baraka",
            last_name="Juma",
            gender=Student.Gender.MALE,
            class_level="Form One",
            parent=other_parent,
            ward="Kayanga",
            village="Town",
            street="Main Road",
        )
        StoreSupplyReceipt.objects.create(
            student=other_student,
            item=StoreSupplyReceipt.Item.MACHETE,
            quantity_collected=100,
            source="Another student's delivery",
        )

        response = self.client.get(
            reverse("student-supply-history", kwargs={"student_id": self.student.pk})
        )

        self.assertEqual(
            response.context["supply_totals"],
            [{"item_label": "Machete", "quantity": 5}],
        )
        self.assertContains(response, "First delivery")
        self.assertContains(response, "Later delivery")
        self.assertNotContains(response, "Another student's delivery")
        self.assertContains(response, "button-edit button-small")

    def test_supply_entry_from_student_history_prefills_and_returns_to_student(self):
        create_url = f"{reverse('supply-create')}?student={self.student.pk}"
        form_response = self.client.get(create_url)

        self.assertContains(
            form_response,
            f'<option value="{self.student.pk}" selected>',
            html=False,
        )

        response = self.client.post(
            create_url,
            {
                "student": self.student.pk,
                "source": "Later delivery",
                "notes": "",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "1",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-item": StoreSupplyReceipt.Item.SICKLE,
                "items-0-quantity_collected": "1",
            },
        )

        self.assertRedirects(
            response,
            reverse("student-supply-history", kwargs={"student_id": self.student.pk}),
        )

    def test_existing_unassigned_receipt_can_be_linked_to_student(self):
        receipt = StoreSupplyReceipt.objects.create(
            item=StoreSupplyReceipt.Item.MACHETE,
            quantity_collected=1,
        )
        list_response = self.client.get(reverse("supply-list"))
        self.assertContains(list_response, "Unassigned")
        self.assertContains(
            list_response,
            reverse("supply-edit", kwargs={"receipt_id": receipt.pk}),
        )

        response = self.client.post(
            reverse("supply-edit", kwargs={"receipt_id": receipt.pk}),
            {
                "student": self.student.pk,
                "source": "",
                "notes": "",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "1",
                "items-MIN_NUM_FORMS": "1",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-item": StoreSupplyReceipt.Item.MACHETE,
                "items-0-quantity_collected": "1",
            },
        )

        receipt.refresh_from_db()
        self.assertRedirects(response, reverse("supply-list"))
        self.assertEqual(receipt.student, self.student)


class StudentClothingWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="registrar-clothing",
            password="test-password",
        )
        login_with_totp(self.client, self.user)
        self.parent = Parent.objects.create(
            full_name="Amina Mwinyi",
            phone_number="0712345678",
        )

    def create_student(self):
        return Student.objects.create(
            admission_number="KSS-CLOTH-1",
            first_name="Neema",
            last_name="Amina",
            gender=Student.Gender.FEMALE,
            class_level="Form One",
            parent=self.parent,
            ward="Kayanga",
            village="Town",
            street="Main Road",
        )

    def test_student_registration_continues_to_clothing_checks(self):
        response = self.client.post(
            reverse("student-create"),
            {
                "admission_number": "KSS-NEW-1",
                "first_name": "Asha",
                "middle_name": "",
                "last_name": "Mwinyi",
                "gender": Student.Gender.FEMALE,
                "class_level": "Form One",
                "parent": self.parent.pk,
                "region": "Kagera",
                "district": "Karagwe",
                "ward": "Kayanga",
                "village": "Town",
                "street": "Main Road",
            },
        )

        student = Student.objects.get(admission_number="KSS-NEW-1")
        self.assertRedirects(
            response,
            reverse("student-clothing", kwargs={"student_id": student.pk}),
        )

    def test_clothing_item_can_be_verified_and_updated(self):
        student = self.create_student()
        response = self.client.post(
            reverse("student-clothing", kwargs={"student_id": student.pk}),
            {
                "category": StudentClothingVerification.Category.SCHOOL_UNIFORM,
                "clothing_item": "School shirt",
                "is_verified": "",
                "notes": "",
            },
        )
        check = StudentClothingVerification.objects.get()
        self.assertRedirects(
            response,
            reverse("student-clothing", kwargs={"student_id": student.pk}),
        )
        self.assertFalse(check.is_verified)

        response = self.client.post(
            reverse(
                "student-clothing-edit",
                kwargs={
                    "student_id": student.pk,
                    "verification_id": check.pk,
                },
            ),
            {
                "category": StudentClothingVerification.Category.SCHOOL_UNIFORM,
                "clothing_item": "School shirt",
                "is_verified": "on",
                "notes": "Correct uniform",
            },
        )
        check.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("student-clothing", kwargs={"student_id": student.pk}),
        )
        self.assertTrue(check.is_verified)
        self.assertEqual(check.verified_by, self.user)
        self.assertIsNotNone(check.verified_at)


class RecordDeletionConfirmationTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="record-manager",
            password="test-password",
        )
        login_with_totp(self.client, user)
        self.parent = Parent.objects.create(
            full_name="Amina Mwinyi",
            phone_number="0712345678",
        )
        self.student = Student.objects.create(
            admission_number="KSS-DELETE-1",
            first_name="Neema",
            last_name="Amina",
            gender=Student.Gender.FEMALE,
            class_level="Form One",
            parent=self.parent,
            ward="Kayanga",
            village="Town",
            street="Main Road",
        )

    def test_collection_delete_requires_confirmation(self):
        collection = StudentCollection.objects.create(
            student=self.student,
            category=StudentCollection.Category.ACADEMIC_FEE,
            amount_collected="15000",
        )
        url = reverse("collection-delete", kwargs={"collection_id": collection.pk})

        confirmation = self.client.get(url)
        self.assertContains(confirmation, "This action cannot be undone.")
        self.assertContains(confirmation, "delete-card")
        self.assertContains(confirmation, "button-delete-confirm")
        self.assertTrue(StudentCollection.objects.filter(pk=collection.pk).exists())

        response = self.client.post(url)

        self.assertRedirects(response, reverse("collection-list"))
        self.assertFalse(StudentCollection.objects.filter(pk=collection.pk).exists())

    def test_student_delete_warns_about_cascaded_activity_records(self):
        StudentCollection.objects.create(
            student=self.student,
            category=StudentCollection.Category.ACADEMIC_FEE,
        )
        StudentClothingVerification.objects.create(
            student=self.student,
            category=StudentClothingVerification.Category.SCHOOL_UNIFORM,
            clothing_item="School shirt",
        )
        url = reverse("student-delete", kwargs={"student_id": self.student.pk})

        confirmation = self.client.get(url)

        self.assertContains(confirmation, "1 collection record(s)")
        self.assertContains(confirmation, "1 clothing check(s)")

        response = self.client.post(url)

        self.assertRedirects(response, reverse("student-list"))
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
        self.assertFalse(StudentCollection.objects.exists())
        self.assertFalse(StudentClothingVerification.objects.exists())

    def test_student_delete_is_blocked_while_supply_records_exist(self):
        receipt = StoreSupplyReceipt.objects.create(
            student=self.student,
            item=StoreSupplyReceipt.Item.HOE,
            quantity_collected=1,
        )
        url = reverse("student-delete", kwargs={"student_id": self.student.pk})

        confirmation = self.client.get(url)
        self.assertContains(confirmation, "Deletion is blocked")

        response = self.client.post(url)

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())
        self.assertTrue(StoreSupplyReceipt.objects.filter(pk=receipt.pk).exists())

    def test_parent_delete_is_blocked_while_students_are_linked(self):
        url = reverse("parent-delete", kwargs={"parent_id": self.parent.pk})

        confirmation = self.client.get(url)
        self.assertContains(confirmation, "Deletion is blocked")

        response = self.client.post(url)

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Parent.objects.filter(pk=self.parent.pk).exists())

    def test_parent_without_students_can_be_deleted_after_confirmation(self):
        self.student.delete()
        url = reverse("parent-delete", kwargs={"parent_id": self.parent.pk})

        confirmation = self.client.get(url)
        self.assertContains(confirmation, "This action cannot be undone.")

        response = self.client.post(url)

        self.assertRedirects(response, reverse("parent-list"))
        self.assertFalse(Parent.objects.filter(pk=self.parent.pk).exists())

    def test_supply_and_clothing_records_have_confirmed_delete_actions(self):
        receipt = StoreSupplyReceipt.objects.create(
            student=self.student,
            item=StoreSupplyReceipt.Item.HOE,
            quantity_collected=1,
        )
        check = StudentClothingVerification.objects.create(
            student=self.student,
            category=StudentClothingVerification.Category.SCHOOL_UNIFORM,
            clothing_item="School shirt",
        )
        supply_url = reverse("supply-delete", kwargs={"receipt_id": receipt.pk})
        clothing_url = reverse(
            "clothing-verification-delete",
            kwargs={
                "student_id": self.student.pk,
                "verification_id": check.pk,
            },
        )

        self.assertContains(self.client.get(supply_url), "This action cannot be undone.")
        self.assertContains(self.client.get(clothing_url), "This action cannot be undone.")
        self.client.post(supply_url)
        self.client.post(clothing_url)
        self.assertFalse(StoreSupplyReceipt.objects.filter(pk=receipt.pk).exists())
        self.assertFalse(StudentClothingVerification.objects.filter(pk=check.pk).exists())


class MFAEnrollmentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mfa-required",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_staff_without_totp_is_redirected_to_authenticator_setup(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("mfa_activate_totp"))

        activation = self.client.get(response["Location"])
        self.assertEqual(activation.status_code, 302)
        self.assertIn(reverse("account_reauthenticate"), activation["Location"])

        reauthentication = self.client.get(activation["Location"])
        self.assertEqual(reauthentication.status_code, 200)

    def test_staff_with_totp_can_open_home(self):
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.TOTP,
            data={"secret": "test-secret"},
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)

    def test_totp_setup_renders_qr_code_for_final_enrollment_step(self):
        session = self.client.session
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {"method": "password", "at": time.time()}
        ]
        session.save()

        response = self.client.get(reverse("mfa_activate_totp"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data:image/svg+xml;base64")


class DeletionReauthenticationTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="mfa-delete",
            password="test-password",
        )
        login_with_totp(self.client, user, recently_authenticated=False)
        parent = Parent.objects.create(full_name="Amina Mwinyi", phone_number="0712345678")
        self.student = Student.objects.create(
            admission_number="KSS-MFA-1",
            first_name="Neema",
            last_name="Amina",
            gender=Student.Gender.FEMALE,
            class_level="Form One",
            parent=parent,
            ward="Kayanga",
            village="Town",
            street="Main Road",
        )

    def test_deletion_requires_mfa_reauthentication_not_only_password(self):
        response = self.client.get(
            reverse("student-delete", kwargs={"student_id": self.student.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("mfa_reauthenticate"), response["Location"])
        self.assertNotIn(reverse("account_reauthenticate"), response["Location"])

    def test_account_deletion_requires_mfa_reauthentication(self):
        response = self.client.get(reverse("account-delete"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("mfa_reauthenticate"), response["Location"])
        self.assertNotIn(reverse("account_reauthenticate"), response["Location"])

    def test_admin_record_delete_also_requires_mfa_reauthentication(self):
        admin_user = get_user_model().objects.create_superuser(
            username="mfa-admin",
            email="admin@example.test",
            password="test-password",
        )
        login_with_totp(self.client, admin_user, recently_authenticated=False)
        url_name = (
            f"admin:{Student._meta.app_label}_{Student._meta.model_name}_delete"
        )
        response = self.client.get(reverse(url_name, args=[self.student.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("mfa_reauthenticate"), response["Location"])
        self.assertNotIn(reverse("account_reauthenticate"), response["Location"])

    def test_admin_dashboard_requires_mfa_even_after_password_reauthentication(self):
        session = self.client.session
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {"method": "password", "at": time.time()}
        ]
        session.save()

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("mfa_reauthenticate"), response["Location"])
        self.assertNotIn(reverse("account_reauthenticate"), response["Location"])
        self.assertIn("next=%2Fadmin%2F", response["Location"])

        mfa_challenge = self.client.get(response["Location"])
        self.assertEqual(mfa_challenge.status_code, 200)


class LogoutMFAReauthenticationTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="mfa-logout",
            password="test-password",
        )
        login_with_totp(self.client, user, recently_authenticated=False)

    def assert_logout_requires_mfa(self, url):
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("mfa_reauthenticate"), response["Location"])
        self.assertNotIn(reverse("account_reauthenticate"), response["Location"])
        challenge = self.client.get(response["Location"])
        self.assertEqual(challenge.status_code, 200)

    def test_account_logout_requires_mfa_reauthentication(self):
        self.assert_logout_requires_mfa(reverse("account_logout"))

    def test_admin_logout_requires_mfa_reauthentication(self):
        self.assert_logout_requires_mfa(reverse("admin:logout"))

    def set_recent_mfa_authentication(self):
        session = self.client.session
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {"method": "mfa", "type": "totp", "at": time.time()}
        ]
        session.save()

    def test_account_logout_redirects_home_after_mfa(self):
        self.set_recent_mfa_authentication()

        response = self.client.post(
            reverse("account_logout"),
            {"next": reverse("admin:index")},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("home"))

    def test_admin_logout_redirects_home_after_mfa(self):
        self.set_recent_mfa_authentication()

        response = self.client.post(
            reverse("admin:logout"),
            {"next": reverse("admin:index")},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("home"))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RecordNotificationTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.creator = get_user_model().objects.create_user(
            username="record-creator",
            email="creator@example.test",
            password="test-password",
        )
        login_with_totp(self.client, self.creator)
        self.parent = Parent.objects.create(
            full_name="Amina Mwinyi",
            phone_number="0712345678",
            created_by=self.creator,
        )
        self.student = Student.objects.create(
            admission_number="KSS-MAIL-1",
            first_name="Neema",
            last_name="Amina",
            gender=Student.Gender.FEMALE,
            class_level="Form One",
            parent=self.parent,
            registered_by=self.creator,
            ward="Kayanga",
            village="Town",
            street="Main Road",
        )

    def assert_pdf_attachment(self, notification):
        filename, attachment, content_type = notification.attachments[0]
        self.assertTrue(filename.endswith(".pdf"))
        self.assertEqual(content_type, "application/pdf")
        self.assertIsInstance(attachment, bytes)
        self.assertTrue(attachment.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", attachment[-32:])
        return attachment

    def test_parent_creation_emails_creator_snapshot_as_pdf(self):
        response = self.client.post(
            reverse("parent-create"),
            {
                "full_name": "Baraka Juma",
                "phone_number": "0700000000",
                "email": "parent@example.test",
            },
        )

        self.assertRedirects(response, reverse("parent-list"))
        self.assertEqual(len(mail.outbox), 1)
        notification = mail.outbox[0]
        self.assertEqual(notification.to, ["creator@example.test"])
        self.assertIn("Parent", notification.body)
        attachment = self.assert_pdf_attachment(notification)
        self.assertIn(b"Baraka Juma", attachment)

    def test_supply_update_notifies_original_creator_with_before_and_after(self):
        actor = get_user_model().objects.create_user(
            username="different-actor",
            email="actor@example.test",
            password="test-password",
        )
        login_with_totp(self.client, actor)
        receipt = StoreSupplyReceipt.objects.create(
            student=self.student,
            item=StoreSupplyReceipt.Item.HOE,
            quantity_collected=2,
            recorded_by=self.creator,
        )

        response = self.client.post(
            reverse("supply-edit", kwargs={"receipt_id": receipt.pk}),
            {
                "student": self.student.pk,
                "source": "Updated source",
                "notes": "Updated notes",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "1",
                "items-MIN_NUM_FORMS": "1",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-item": StoreSupplyReceipt.Item.HOE,
                "items-0-quantity_collected": "4",
            },
        )

        self.assertRedirects(response, reverse("supply-list"))
        self.assertEqual(len(mail.outbox), 1)
        notification = mail.outbox[0]
        self.assertEqual(notification.to, ["creator@example.test"])
        self.assertIn("updated", notification.subject)
        self.assertIn('"before"', notification.body)
        self.assertIn('"after"', notification.body)

    def test_email_failure_keeps_record_and_shows_warning(self):
        with patch(
            "ContributionSystem.notifications.EmailMessage.send",
            side_effect=SMTPException("mail server unavailable"),
        ):
            response = self.client.post(
                reverse("parent-create"),
                {
                    "full_name": "Baraka Juma",
                    "phone_number": "0700000000",
                    "email": "",
                },
                follow=True,
            )

        self.assertTrue(Parent.objects.filter(full_name="Baraka Juma").exists())
        self.assertContains(response, "email notification could not be sent")

    def test_deletion_emails_original_creator_snapshot(self):
        collection = StudentCollection.objects.create(
            student=self.student,
            category=StudentCollection.Category.ACADEMIC_FEE,
            amount_collected="25000",
            recorded_by=self.creator,
        )
        url = reverse("collection-delete", kwargs={"collection_id": collection.pk})

        response = self.client.post(url)

        self.assertRedirects(response, reverse("collection-list"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["creator@example.test"])
        self.assertIn("deleted", mail.outbox[0].subject)
        self.assert_pdf_attachment(mail.outbox[0])

    def test_student_deletion_email_includes_cascaded_record_data(self):
        StudentCollection.objects.create(
            student=self.student,
            category=StudentCollection.Category.ACADEMIC_FEE,
            amount_collected="25000",
        )
        StudentClothingVerification.objects.create(
            student=self.student,
            category=StudentClothingVerification.Category.SCHOOL_UNIFORM,
            clothing_item="School shirt",
        )

        response = self.client.post(
            reverse("student-delete", kwargs={"student_id": self.student.pk})
        )

        self.assertRedirects(response, reverse("student-list"))
        self.assertEqual(len(mail.outbox), 1)
        attachment = self.assert_pdf_attachment(mail.outbox[0])
        self.assertIn(b"School shirt", attachment)
        self.assertIn(b"25000", attachment)


class LanguageSwitchTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="bilingual-staff",
            password="test-password",
        )
        login_with_totp(self.client, user)

    def test_language_switch_translates_home_and_can_switch_back(self):
        response = self.client.post(
            reverse("set_language"),
            {"language": "sw", "next": reverse("home")},
        )

        self.assertRedirects(response, reverse("home"))
        swahili_home = self.client.get(reverse("home"))
        self.assertContains(swahili_home, 'lang="sw"')
        self.assertContains(swahili_home, "Karibu Shule ya Sekondari ya Kafunjo")
        self.assertContains(swahili_home, "Wanafunzi")
        student_form = self.client.get(reverse("student-create"))
        self.assertContains(student_form, "Jina la kwanza")
        self.assertContains(student_form, "Mwanamke")
        profile = self.client.get(reverse("profile"))
        self.assertContains(profile, "Wasifu wangu")

        response = self.client.post(
            reverse("set_language"),
            {"language": "en-us", "next": reverse("home")},
        )

        self.assertRedirects(response, reverse("home"))
        english_home = self.client.get(reverse("home"))
        self.assertContains(english_home, 'lang="en-us"')
        self.assertContains(english_home, "Welcome to Kafunjo Secondary School")

    def test_model_choices_use_the_selected_language(self):
        with translation.override("sw"):
            self.assertEqual(str(Student.Gender.choices[0][1]), "Mwanamke")


class SchoolRoleAccessTests(TestCase):
    def setUp(self):
        self.parent = Parent.objects.create(
            full_name="Amina Mwinyi",
            phone_number="0712345678",
        )
        self.student = Student.objects.create(
            admission_number="KSS-ROLE-1",
            first_name="Neema",
            last_name="Amina",
            gender=Student.Gender.FEMALE,
            class_level="Form One",
            parent=self.parent,
            ward="Kayanga",
            village="Town",
            street="Main Road",
        )

    def create_role_user(self, username, *roles):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password",
        )
        login_with_totp(self.client, user, roles=roles)
        return user

    def test_academic_can_manage_only_academic_fee_collections(self):
        user = self.create_role_user("academic-role-user", ACADEMIC_ROLE)
        academic_collection = StudentCollection.objects.create(
            student=self.student,
            category=StudentCollection.Category.ACADEMIC_FEE,
            recorded_by=user,
        )
        StudentCollection.objects.create(
            student=self.student,
            category=StudentCollection.Category.TSHIRT,
        )
        StudentCollection.objects.create(
            student=self.student,
            category=StudentCollection.Category.REAM_A4,
        )

        request = RequestFactory().get("/")
        request.user = user
        self.assertEqual(
            SchoolAccountAdapter().get_login_redirect_url(request),
            reverse("collection-list"),
        )

        response = self.client.get(reverse("collection-list"))
        self.assertContains(response, "Academic fee")
        self.assertNotContains(response, "T-shirt")
        self.assertNotContains(response, "A4 ream")

        form_response = self.client.get(reverse("collection-create"))
        category_choices = {
            value
            for value, _ in form_response.context["form"].fields["category"].choices
        }
        self.assertEqual(category_choices - {""}, {
            StudentCollection.Category.ACADEMIC_FEE,
        })

        invalid_response = self.client.post(
            reverse("collection-create"),
            {
                "student": self.student.pk,
                "category": StudentCollection.Category.TSHIRT,
                "amount_collected": "0",
                "quantity_issued": "1",
                "notes": "",
            },
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertEqual(StudentCollection.objects.count(), 3)
        self.assertEqual(
            self.client.get(
                reverse("collection-edit", args=[2]),
            ).status_code,
            404,
        )
        self.assertEqual(self.client.get(reverse("student-list")).status_code, 403)

        with patch("ContributionSystem.views.send_record_notification"):
            self.client.post(
                reverse("collection-edit", args=[academic_collection.pk]),
                {
                    "student": self.student.pk,
                    "category": StudentCollection.Category.ACADEMIC_FEE,
                    "amount_collected": "12500",
                    "quantity_issued": "0",
                    "notes": "Updated by academic",
                },
            )
        academic_collection.refresh_from_db()
        self.assertEqual(academic_collection.amount_collected, 12500)

    def test_accountant_can_manage_only_assigned_collection_categories(self):
        self.create_role_user("accountant-role-user", ACCOUNTANT_ROLE)
        for category in StudentCollection.Category.values:
            StudentCollection.objects.create(
                student=self.student,
                category=category,
            )

        response = self.client.get(reverse("collection-list"))
        self.assertContains(response, "T-shirt")
        self.assertContains(response, "School guard fee")
        self.assertContains(response, "Necktie")
        self.assertContains(response, "Table")
        self.assertContains(response, "Chair")
        self.assertNotContains(response, "Academic fee")
        self.assertNotContains(response, "A4 ream")
        self.assertNotContains(response, "Logo")
        self.assertEqual(self.client.get(reverse("student-list")).status_code, 403)

    def test_second_head_can_manage_student_registration_and_uniform_checks(self):
        user = self.create_role_user("second-head-role-user", SECOND_HEAD_ROLE)
        request = RequestFactory().get("/")
        request.user = user
        self.assertEqual(
            SchoolAccountAdapter().get_login_redirect_url(request),
            reverse("student-list"),
        )

        self.assertEqual(self.client.get(reverse("student-list")).status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("student-edit", args=[self.student.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("student-clothing", args=[self.student.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("collection-list")).status_code,
            403,
        )

        with patch("ContributionSystem.views.send_record_notification"):
            self.client.post(
                reverse("student-edit", args=[self.student.pk]),
                {
                    "admission_number": self.student.admission_number,
                    "first_name": "Updated",
                    "middle_name": "",
                    "last_name": self.student.last_name,
                    "gender": Student.Gender.FEMALE,
                    "date_of_birth": "",
                    "class_level": self.student.class_level,
                    "parent": self.parent.pk,
                    "region": self.student.region,
                    "district": self.student.district,
                    "ward": self.student.ward,
                    "village": self.student.village,
                    "street": self.student.street,
                },
            )
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Updated")

    def test_users_without_exactly_one_role_cannot_open_role_pages(self):
        user = self.create_role_user(
            "multi-role-user",
            ACADEMIC_ROLE,
            SECOND_HEAD_ROLE,
        )
        request = RequestFactory().get("/")
        request.user = user

        self.assertEqual(
            SchoolAccountAdapter().get_login_redirect_url(request),
            reverse("profile"),
        )
        self.assertEqual(self.client.get(reverse("student-list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("collection-list")).status_code, 403)


class SocialLoginTests(TestCase):
    @override_settings(SOCIALACCOUNT_PROVIDERS={})
    def test_login_page_works_without_social_credentials(self):
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Or use a third-party")

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {
                "APP": {"client_id": "google-client", "secret": "google-secret"}
            },
            "microsoft": {
                "APP": {"client_id": "microsoft-client", "secret": "microsoft-secret"}
            },
            "github": {
                "APP": {"client_id": "github-client", "secret": "github-secret"}
            },
            "amazon": {
                "APP": {"client_id": "amazon-client", "secret": "amazon-secret"}
            },
        }
    )
    def test_login_page_offers_configured_social_providers(self):
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        for provider in ("Google", "Microsoft", "GitHub", "Amazon"):
            self.assertContains(response, provider)


class ContentSecurityPolicyTests(TestCase):
    def assert_script_tags_use_nonce(self, response):
        nonce = response.wsgi_request.csp_nonce
        parser = ScriptNonceParser()
        parser.feed(response.content.decode())
        executable_scripts = [
            attrs
            for attrs in parser.script_attributes
            if attrs.get("type") != "application/json"
        ]

        self.assertTrue(executable_scripts)
        for attrs in executable_scripts:
            self.assertEqual(attrs.get("nonce"), nonce)

    def test_scripts_use_strict_dynamic_and_response_nonces(self):
        for url in (reverse("home"), reverse("account_login")):
            response = self.client.get(url)
            nonce = response.wsgi_request.csp_nonce

            self.assertIn(
                f"script-src 'nonce-{nonce}' 'strict-dynamic' 'self'",
                response.headers["Content-Security-Policy"],
            )
            self.assertNotIn(
                "'unsafe-inline'",
                response.headers["Content-Security-Policy"],
            )
            self.assert_script_tags_use_nonce(response)

    @override_settings(
        UMAMI_SCRIPT_URL="https://analytics.example/script.js",
        UMAMI_WEBSITE_ID="umami-test-site",
        SECURE_CSP={
            **settings.SECURE_CSP,
            "script-src": settings.SECURE_CSP["script-src"]
            + ["https://analytics.example"],
            "connect-src": settings.SECURE_CSP["connect-src"]
            + ["https://analytics.example"],
        },
    )
    def test_umami_uses_nonce_and_tracks_only_named_routes(self):
        for path, page_name in (
            (reverse("home"), "home"),
            (reverse("account_login"), "account_login"),
        ):
            response = self.client.get(f"{path}?q=private-record")
            parser = ScriptNonceParser()
            parser.feed(response.content.decode())
            tracker = next(
                attrs
                for attrs in parser.script_attributes
                if "data-umami-tracker" in attrs
            )
            nonce = response.wsgi_request.csp_nonce
            policy = response.headers["Content-Security-Policy"]

            self.assertEqual(tracker.get("src"), "https://analytics.example/script.js")
            self.assertEqual(tracker.get("data-website-id"), "umami-test-site")
            self.assertEqual(tracker.get("data-page-name"), page_name)
            self.assertEqual(tracker.get("data-auto-track"), "false")
            self.assertEqual(tracker.get("nonce"), nonce)
            self.assertNotIn("private-record", str(tracker))
            self.assert_script_tags_use_nonce(response)
            self.assertIn("connect-src 'self' https://analytics.example", policy)
            self.assertIn(
                f"script-src 'nonce-{nonce}' 'strict-dynamic' 'self' "
                "https://analytics.example",
                policy,
            )

    @override_settings(UMAMI_SCRIPT_URL="", UMAMI_WEBSITE_ID="")
    def test_umami_is_not_loaded_without_configuration(self):
        response = self.client.get(reverse("home"))

        self.assertNotContains(response, "data-umami-tracker")
        self.assertNotContains(response, "umami-pageview.js")

    def test_allauth_account_and_mfa_scripts_use_response_nonces(self):
        user = get_user_model().objects.create_user(
            username="csp-nonce-user",
            password="test-password",
        )
        login_with_totp(self.client, user)
        generate_codes_response = self.client.post(
            reverse("mfa_generate_recovery_codes")
        )
        self.assertEqual(generate_codes_response.status_code, 302)

        for route_name in (
            "account_email",
            "mfa_view_recovery_codes",
        ):
            response = self.client.get(reverse(route_name))

            self.assertEqual(response.status_code, 200, route_name)
            self.assert_script_tags_use_nonce(response)

    def test_allauth_webauthn_scripts_use_response_nonce(self):
        nonce = "test-csp-nonce"
        request = RequestFactory().get("/")
        request.csp_nonce = nonce
        request.user = AnonymousUser()
        markup = render_to_string(
            "mfa/webauthn/snippets/scripts.html",
            request=request,
        )
        parser = ScriptNonceParser()
        parser.feed(markup)

        self.assertEqual(len(parser.script_attributes), 3)
        for attrs in parser.script_attributes:
            self.assertEqual(attrs.get("nonce"), nonce)

    def test_form_action_allows_google_oauth_redirect(self):
        response = self.client.get(reverse("account_login"))

        self.assertIn(
            "form-action 'self' https://mavumba.pythonanywhere.com "
            "https://accounts.google.com",
            response.headers["Content-Security-Policy"],
        )

    def test_htmx_indicator_styles_use_the_response_nonce(self):
        response = self.client.get(reverse("home"))
        nonce = response.wsgi_request.csp_nonce

        self.assertContains(
            response,
            f'htmx.config.inlineStyleNonce = "{nonce}"',
        )
        self.assertContains(
            response,
            f'htmx.config.inlineScriptNonce = "{nonce}"',
        )
        self.assertIn(
            f"style-src 'self' 'nonce-{nonce}'",
            response.headers["Content-Security-Policy"],
        )


class AdminBrandingTests(TestCase):
    def test_school_branding_appears_on_admin_login_and_dashboard(self):
        response = self.client.get(reverse("admin:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kafunjo Secondary School Administration")
        self.assertContains(response, "Kafunjo Secondary School Admin Portal")

        user = get_user_model().objects.create_user(
            username="admin-branding-user",
            password="test-password",
        )
        login_with_totp(self.client, user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kafunjo Secondary School Administration")
        self.assertContains(response, "School Management Dashboard")
        self.assertContains(response, reverse("library:dashboard"))
        self.assertContains(response, "Library management")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountRecoveryTests(TestCase):
    def test_recovery_request_is_submitted_without_account_lookup(self):
        admin = get_user_model().objects.create_user(
            username="recovery-admin",
            email="admin@example.test",
            password="test-password",
            is_staff=True,
        )
        response = self.client.post(
            reverse("account-recovery"),
            {"email": "unknown@example.test"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Request received")
        request = AccountRecoveryRequest.objects.get()
        self.assertEqual(request.email, "unknown@example.test")
        self.assertEqual(request.status, AccountRecoveryRequest.Status.PENDING)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [admin.email])
        self.assertIn(request.email, mail.outbox[0].body)

    def test_recovery_request_warns_when_no_administrator_email_is_available(self):
        response = self.client.post(
            reverse("account-recovery"),
            {"email": "unknown@example.test"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(AccountRecoveryRequest.objects.exists())
        self.assertContains(response, "administrators could not be notified")
        self.assertEqual(mail.outbox, [])

    def test_recovery_request_is_saved_when_email_delivery_fails(self):
        get_user_model().objects.create_user(
            username="recovery-admin",
            email="admin@example.test",
            password="test-password",
            is_staff=True,
        )
        with patch(
            "ContributionSystem.notifications.EmailMessage.send",
            side_effect=SMTPException("mail server unavailable"),
        ):
            response = self.client.post(
                reverse("account-recovery"),
                {"email": "unknown@example.test"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(AccountRecoveryRequest.objects.exists())
        self.assertContains(response, "email notification could not be sent")

    def test_login_and_home_link_to_account_recovery(self):
        self.assertContains(
            self.client.get(reverse("account_login")),
            reverse("account-recovery"),
        )
        self.assertContains(
            self.client.get(reverse("home")),
            reverse("account-recovery"),
        )


class AccountDeletionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="account-delete-user",
            password="test-password",
        )
        login_with_totp(self.client, self.user, recently_authenticated=True)

    def test_confirmation_page_explains_permanent_account_deletion(self):
        response = self.client.get(reverse("account-delete"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This action cannot be undone.")
        self.assertContains(response, 'name="confirm_deletion"')
        self.assertContains(response, "reauthenticate with MFA")

    def test_account_deletion_requires_mfa_enrollment(self):
        user = get_user_model().objects.create_user(
            username="account-delete-without-mfa",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("account-delete"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("mfa_activate_totp"))
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())

    def test_account_is_not_deleted_without_explicit_confirmation(self):
        response = self.client.post(reverse("account-delete"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            get_user_model().objects.filter(pk=self.user.pk).exists()
        )

    def test_mfa_reauthenticated_user_can_delete_account(self):
        response = self.client.post(
            reverse("account-delete"),
            {"confirm_deletion": "on"},
        )

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(
            get_user_model().objects.filter(pk=self.user.pk).exists()
        )
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class UserProfileTests(TestCase):
    def test_accounts_namespace_alias_resolves_existing_routes(self):
        self.assertEqual(reverse("accounts:profile"), reverse("profile"))
        self.assertEqual(
            reverse("accounts:account_login"),
            reverse("account_login"),
        )

    def test_authenticated_homepage_links_to_the_user_profile(self):
        user = get_user_model().objects.create_user(
            username="homepage-profile-user",
            password="test-password",
        )
        login_with_totp(self.client, user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("profile"))
        self.assertContains(response, "View my profile")
        self.assertContains(response, "My profile")
        self.assertContains(response, "Good to see you, homepage-profile-user")
        self.assertContains(response, 'class="live-clock"')
        self.assertContains(response, "Africa/Dar_es_Salaam")
        for route_name in (
            "student-list",
            "collection-list",
            "supply-list",
        ):
            self.assertContains(response, reverse(route_name))

    def test_superuser_homepage_links_to_user_management(self):
        user = get_user_model().objects.create_user(
            username="homepage-admin-user",
            password="test-password",
        )
        login_with_totp(self.client, user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("admin:auth_user_changelist"))
        self.assertContains(response, "Manage users")

    def test_non_superuser_homepage_hides_user_management_link(self):
        user = get_user_model().objects.create_user(
            username="homepage-standard-user",
            password="test-password",
        )
        login_with_totp(self.client, user, roles=())

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("admin:auth_user_changelist"))
        self.assertNotContains(response, "Manage users")

    def test_unauthenticated_homepage_hides_student_and_collection_actions(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("account_login"))
        self.assertNotContains(response, 'class="live-clock"')
        for route_name in (
            "student-list",
            "student-create",
            "parent-list",
            "collection-list",
            "supply-list",
        ):
            self.assertNotContains(response, reverse(route_name))

    def test_signed_in_user_without_school_role_sees_access_notice(self):
        user = get_user_model().objects.create_user(
            username="unassigned-user",
            password="test-password",
        )
        login_with_totp(self.client, user, roles=())

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no school role is assigned")
        self.assertNotContains(response, reverse("student-list"))
        self.assertNotContains(response, reverse("collection-list"))

    def test_profile_shows_logged_in_users_details_and_security_status(self):
        user = get_user_model().objects.create_user(
            username="profile-user",
            email="profile@example.test",
            first_name="Amina",
            last_name="Mwinyi",
            password="test-password",
        )
        login_with_totp(self.client, user)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Amina Mwinyi")
        self.assertContains(response, "profile@example.test")
        self.assertContains(response, "profile-user")
        self.assertContains(response, "An authenticator app is connected")
        self.assertContains(response, "Good to see you, Amina")
        self.assertContains(response, 'class="live-clock"')
        self.assertContains(response, reverse("account_email"))
        self.assertContains(response, reverse("account_change_password"))
        self.assertContains(response, reverse("mfa_index"))
        self.assertContains(response, reverse("account-delete"))

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))

        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={reverse('profile')}",
        )

    def test_profile_can_update_username_and_names(self):
        user = get_user_model().objects.create_user(
            username="profile-edit-user",
            password="test-password",
        )
        login_with_totp(self.client, user)

        response = self.client.post(
            reverse("profile-edit"),
            {
                "username": "updated-profile-user",
                "first_name": "Amina",
                "last_name": "Mwinyi",
            },
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(user.username, "updated-profile-user")
        self.assertEqual(user.first_name, "Amina")
        self.assertEqual(user.last_name, "Mwinyi")

    def test_profile_has_allauth_logout_post_button(self):
        user = get_user_model().objects.create_user(
            username="profile-logout-user",
            password="test-password",
        )
        login_with_totp(self.client, user)

        response = self.client.get(reverse("profile"))

        self.assertContains(
            response,
            f'action="{reverse("account_logout")}"',
        )
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_allauth_logout_button_signs_the_user_out(self):
        user = get_user_model().objects.create_user(
            username="profile-logout-post-user",
            password="test-password",
        )
        login_with_totp(self.client, user)

        response = self.client.post(reverse("account_logout"))

        self.assertIn(response.status_code, (302, 303))
        self.assertFalse(response.wsgi_request.user.is_authenticated)
