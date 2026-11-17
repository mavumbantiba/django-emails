from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path.cwd()
DESTINATION = ROOT / "PROJECT_DOCUMENTATION.pdf"
FONTS = Path(r"C:\Windows\Fonts")
pdfmetrics.registerFont(TTFont("Guide", str(FONTS / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Guide-Bold", str(FONTS / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Guide-Italic", str(FONTS / "ariali.ttf")))
pdfmetrics.registerFontFamily(
    "Guide", normal="Guide", bold="Guide-Bold",
    italic="Guide-Italic", boldItalic="Guide-Bold",
)

NAVY = colors.HexColor("#142f45")
BLUE = colors.HexColor("#2362a6")
GREEN = colors.HexColor("#167a51")
MUTED = colors.HexColor("#526575")
PALE = colors.HexColor("#eef4f7")
LINE = colors.HexColor("#d9e3e9")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="CoverTitle", fontName="Guide-Bold", fontSize=28, leading=34,
    textColor=NAVY, alignment=TA_LEFT, spaceAfter=12,
))
styles.add(ParagraphStyle(
    name="CoverSub", fontName="Guide", fontSize=13, leading=20,
    textColor=MUTED, spaceAfter=18,
))
styles.add(ParagraphStyle(
    name="Section", fontName="Guide-Bold", fontSize=19, leading=24,
    textColor=NAVY, spaceBefore=12, spaceAfter=10, keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="Subsection", fontName="Guide-Bold", fontSize=13, leading=17,
    textColor=BLUE, spaceBefore=10, spaceAfter=5, keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="File", fontName="Guide-Bold", fontSize=9.2, leading=12,
    textColor=GREEN, spaceBefore=6, spaceAfter=2, keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="BodyGuide", fontName="Guide", fontSize=9, leading=13,
    textColor=colors.HexColor("#253746"), spaceAfter=6, splitLongWords=True,
))
styles.add(ParagraphStyle(
    name="TOCGuide", fontName="Guide", fontSize=10, leading=14,
    textColor=NAVY, leftIndent=8, firstLineIndent=-8, spaceAfter=4,
))
styles.add(ParagraphStyle(
    name="TOCSubGuide", fontName="Guide", fontSize=8.5, leading=12,
    textColor=MUTED, leftIndent=22, firstLineIndent=-10, spaceAfter=3,
))
styles.add(ParagraphStyle(
    name="CalloutGuide", fontName="Guide-Bold", fontSize=9, leading=13,
    textColor=NAVY, backColor=PALE, borderColor=LINE, borderWidth=0.6,
    borderPadding=8, spaceBefore=5, spaceAfter=9,
))
styles.add(ParagraphStyle(
    name="CodeLabelGuide", fontName="Guide-Bold", fontSize=8.5, leading=11,
    textColor=GREEN, spaceBefore=5, spaceAfter=2,
))
styles.add(ParagraphStyle(
    name="CodeGuide", fontName="Courier", fontSize=7.6, leading=10,
    textColor=NAVY, backColor=PALE, borderColor=LINE, borderWidth=0.5,
    borderPadding=7, spaceBefore=2, spaceAfter=7,
))


def safe(value):
    return escape(str(value)).replace("\n", "<br/>")


class GuideDocument(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(
            path, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
            topMargin=20*mm, bottomMargin=18*mm,
            title="Kafunjo Secondary School Portal - Project Documentation",
            author="Project documentation",
        )
        frame = Frame(
            self.leftMargin, self.bottomMargin, self.width, self.height,
            id="content",
        )
        self.addPageTemplates([
            PageTemplate(id="normal", frames=[frame], onPage=self.page_chrome),
        ])

    def page_chrome(self, canvas, doc):
        if doc.page == 1:
            return
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(LINE)
        canvas.line(18*mm, height-14*mm, width-18*mm, height-14*mm)
        canvas.setFont("Guide-Bold", 7.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(
            18*mm, height-11*mm, "KAFUNJO SECONDARY SCHOOL  /  PROJECT GUIDE",
        )
        canvas.line(18*mm, 13*mm, width-18*mm, 13*mm)
        canvas.setFont("Guide", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            18*mm, 8.5*mm, "Internal reading guide · generated from this repository",
        )
        canvas.drawRightString(width-18*mm, 8.5*mm, f"Page {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        name = flowable.style.name
        if name not in ("Section", "Subsection"):
            return
        level = 0 if name == "Section" else 1
        title = flowable.getPlainText()
        key = f"toc-{self.page}-{len(title)}-{abs(hash(title))}"
        self.canv.bookmarkPage(key)
        if level == 0:
            self.canv.addOutlineEntry(title, key, level=0, closed=False)
        self.notify("TOCEntry", (level, title, self.page, key))


story = []


def section(title):
    story.append(Paragraph(safe(title), styles["Section"]))


def subsection(title):
    story.append(Paragraph(safe(title), styles["Subsection"]))


def paragraph(text):
    story.append(Paragraph(safe(text), styles["BodyGuide"]))


def note(text):
    story.append(Paragraph(safe(text), styles["CalloutGuide"]))


def code(label, text):
    story.append(Paragraph(safe(label), styles["CodeLabelGuide"]))
    story.append(Preformatted(text.strip("\n"), styles["CodeGuide"], maxLineLength=96))


def file(path, description):
    story.append(Paragraph(safe(path), styles["File"]))
    story.append(Paragraph(safe(description), styles["BodyGuide"]))


def file_section(title, entries):
    subsection(title)
    for path, description in entries:
        file(path, description)


# Cover and dynamic contents.
story.extend([
    Spacer(1, 28*mm),
    Paragraph("Kafunjo Secondary School<br/>Project Guide", styles["CoverTitle"]),
    Paragraph(
        "A practical, file-by-file guide to the Django portal: what its parts do, "
        "how requests move through the code, how data is stored, and how to "
        "review or extend the project.",
        styles["CoverSub"],
    ),
    Paragraph(
        "Prepared 17 November 2026 · Covers maintained application source, "
        "templates, migrations, tests, configuration examples, translations, "
        "and first-party assets. It describes current code, not a proposed redesign.",
        styles["CalloutGuide"],
    ),
])
paragraph(
    "This guide is written for a developer or school maintainer who wants to "
    "follow a feature from the browser request through authorization, forms, "
    "database operations, templates, and tests. The guide explains code units "
    "and file responsibilities; it does not duplicate every source line. "
    "Source code remains the definitive reference."
)
paragraph(
    "Generated caches, private environment values, database contents, and "
    "machine-specific diagnostics are intentionally not reproduced."
)
story.append(PageBreak())
section("Contents")
toc = TableOfContents()
toc.levelStyles = [styles["TOCGuide"], styles["TOCSubGuide"]]
story.append(toc)
story.append(PageBreak())

section("1. Project at a glance")
paragraph(
    "This Django application supports Kafunjo Secondary School. The root "
    "configuration combines two first-party apps: ContributionSystem handles "
    "students, parents, contributions, clothing verification, store supplies, "
    "accounts, and the school homepage; LibraryManagement handles the book "
    "catalog and circulation."
)
paragraph(
    "Django provides routing, ORM, forms, sessions, messages, templates, admin, "
    "and migrations. django-allauth provides account sign-in, email verification, "
    "password reset, social sign-in, MFA, and reauthentication. ReportLab creates "
    "PDF audit/email reports and is declared in requirements-pdf.txt."
)
code(
    "High-level request path",
    "Browser -> KAfunjoSecondarySchool1/urls.py -> app urls.py\n"
    "-> middleware and authorization -> view -> form/model/query\n"
    "-> template + messages -> HTTP response",
)
paragraph(
    "The portal and library have distinct layouts but share the same Django "
    "users, sessions, messages, and browser theme preference. Most state-changing "
    "forms use POST and CSRF tokens. HTMX refreshes selected list fragments; "
    "standard page rendering remains available."
)
subsection("Main routes")
for item in [
    "/ — public portal landing page and role-dependent signed-in shortcuts.",
    "/parents/, /students/, /collections/, /supplies/ — school records and contribution workflows.",
    "/accounts/ and /accounts/profile/ — allauth and project profile/security screens.",
    "/accounts/recovery/ — public request for human account-recovery review; it does not reset MFA.",
    "/library/ — catalog; /library/loans/ — issue and return circulation.",
    "/admin/ — Django administration with school branding and sensitive-action reauthentication.",
]:
    paragraph(item)

section("2. Architecture and request flow")
subsection("URL dispatch")
paragraph(
    "KAfunjoSecondarySchool1/urls.py mounts LibraryManagement under /library/, "
    "ContributionSystem at the root, and also exposes a namespaced account-route "
    "alias. App urls.py modules bind URL patterns and names to views. Templates "
    "normally reverse named URLs instead of hardcoding paths."
)
subsection("Middleware, access, and validation")
paragraph(
    "Middleware handles concerns shared by many requests: authentication/session "
    "state, the per-response CSP nonce/security headers, and TOTP enrollment and "
    "admin MFA requirements. View decorators then apply login, school-role, or "
    "library-staff permissions. A signed-in user can still receive a 403 when "
    "their role is not permitted."
)
paragraph(
    "Forms parse and validate submitted values before persistence. Critical "
    "circulation stock checks are repeated inside a transaction with rows locked; "
    "available choices shown by a form alone cannot prevent races between users."
)
subsection("Persistence and presentation")
paragraph(
    "Models define stored records, relationships, constraints, and deletion "
    "behavior. Views select and prepare data, then render a full page or an HTMX "
    "fragment. Django's messages framework communicates success and recoverable "
    "errors across redirects."
)
subsection("Model relationships")
for item in [
    "Parent -> Student: each student requires a parent/guardian; referenced parents cannot be deleted.",
    "Student -> collections and clothing checks: those dependent rows cascade on student deletion.",
    "Student -> supply receipt: optional reference protected from deleting a referenced student.",
    "User attribution generally uses SET_NULL so school history remains when an account is deleted.",
    "Book -> BookLoan -> Student: book and student deletion are protected while loan history references them.",
    "Book.total_copies is title stock; BookLoan.book_number identifies the physical copy, such as 01/100.",
    "AccountRecoveryRequest stores email, review status, and request time; it is a review queue, not a reset token.",
]:
    paragraph(item)

section("3. Authentication, roles, and safety")
subsection("Sign-in and MFA")
paragraph(
    "KAfunjoSecondarySchool1/settings.py configures allauth, verified email, "
    "email sign-in codes, social providers, password validation, and MFA "
    "(TOTP, WebAuthn/passkeys, and recovery codes). RequireTOTPEnrollmentMiddleware "
    "routes signed-in accounts without TOTP through enrollment. Sensitive actions "
    "require recent MFA reauthentication rather than relying on an old login or "
    "password-only challenge."
)
subsection("School roles and recovery")
paragraph(
    "ContributionSystem.access.py resolves Academic, Second Head of School, "
    "and Accountant/Clerk roles and restricts data/category access. "
    "LibraryManagement.access.py allows authenticated staff, superusers, or "
    "users in the approved school groups."
)
paragraph(
    "For lost credentials, users can try verified-email password reset or a "
    "previously saved MFA recovery code. If all factors are lost, the public "
    "recovery form creates a pending human-review request and emails active "
    "staff accounts that have email addresses. If delivery cannot be completed, "
    "the request remains saved and the user is warned to contact the school "
    "office. The application does not automatically bypass MFA; when registered "
    "email is unavailable, the school office must verify the requester using its "
    "identity process."
)
subsection("Security and deployment reminders")
paragraph(
    "Before deployment, review Django's deployment checklist and validate "
    "secret management, ALLOWED_HOSTS, HTTPS, secure cookies, email delivery, "
    "database backups, and social provider callback URLs. settings.py defines "
    "secret-key configuration in source; production should use an approved "
    "secret-management approach. Never copy .env values into documentation."
)
paragraph(
    "ResponseSecurityHeadersMiddleware generates a nonce for each response and "
    "renders the Content-Security-Policy. New inline scripts/styles should use "
    "request.csp_nonce; do not weaken the policy with unsafe-inline. Optional "
    "Umami and social providers are reflected in the CSP configuration."
)

section("4. Root and Django project files")
for path, desc in [
    ("manage.py", "Django command launcher. Sets DJANGO_SETTINGS_MODULE, imports execute_from_command_line, and forwards CLI arguments. Use this for runserver, test, check, migrate, and makemigrations."),
    ("main.py", "Empty tracked placeholder in this snapshot; it is not the Django command entry point."),
    ("requirements-pdf.txt", "Declares ReportLab. It is not a full pinned runtime manifest for the Django web application."),
    (".env.example", "Safe placeholder configuration for SMTP, optional Google/Microsoft/GitHub/Amazon sign-in, and Umami. Store live values only in private environment configuration."),
    (".gitignore", "Excludes local envs, virtual environments, caches, SQLite journals, collected static output, and common build/test artifacts. Ignore rules do not untrack files already committed."),
    (".vscode/settings.json", "Editor settings for terminal environment-file use and unittest discovery."),
    ("THIRD_PARTY_NOTICES.txt", "MIT notice for local allauth template overrides adapted from django-allauth 65.19.2."),
    ("db.sqlite3", "Local SQLite data file used by default settings. It is data, not source; protect it and use migrations rather than manual edits."),
    ("KAfunjoSecondarySchool1/__init__.py", "Python package marker."),
    ("KAfunjoSecondarySchool1/settings.py", "Central configuration: loads approved environment keys, validates optional Umami values, declares apps/middleware, CSP/security headers, auth/MFA/account settings, template context processors, SQLite, validators, localization/time zone, static/media paths, and SMTP."),
    ("KAfunjoSecondarySchool1/urls.py", "Root route composition for admin, namespaced library routes, main ContributionSystem routes, and account namespace alias."),
    ("KAfunjoSecondarySchool1/asgi.py", "Builds the ASGI application callable for ASGI servers."),
    ("KAfunjoSecondarySchool1/wsgi.py", "Builds the WSGI application callable for WSGI hosting."),
    ("KAfunjoSecondarySchool1/# Agent Host Network Diagnostics.md", "Machine-specific diagnostic report; excluded from the guide because it is not application behavior and may expose local environment details."),
]:
    file(path, desc)
note(
    "There is no complete tracked dependency lock/requirements file for the "
    "Django application. requirements-pdf.txt declares ReportLab only; use "
    "the deployment's established dependency setup for Django and allauth."
)

section("5. ContributionSystem files")
paragraph(
    "This app owns school records, roles, account/profile flows, security "
    "middleware, and record-change notifications."
)
for path, desc in [
    ("ContributionSystem/__init__.py", "Python package marker."),
    ("ContributionSystem/apps.py", "Registers the school-records Django app."),
    ("ContributionSystem/models.py", "Defines Parent, Student, StudentCollection, StoreSupplyReceipt, StudentClothingVerification, and AccountRecoveryRequest. Fields capture contact/student/address, contribution and supply details, clothing checks, attribution, and recovery-review state. Foreign-key on_delete rules define what survives deletion; Meta sections define sorting and related names."),
    ("ContributionSystem/forms.py", "Recovery, confirmed deletion, profile, parent, student, collection, supply, and clothing forms. Adds field labels/widgets, role-limited categories, and positive quantity validation."),
    ("ContributionSystem/access.py", "Role constants/helpers, role resolution, permitted collection categories, and role_required view decorators."),
    ("ContributionSystem/adapters.py", "Custom allauth adapter: redirects authenticated school users by role and restricts sensitive delete/logout reauthentication to MFA methods."),
    ("ContributionSystem/security.py", "Checks allauth authentication records for recent MFA, wraps protected views, and strips supplied redirect targets in forced logout flows."),
    ("ContributionSystem/middleware.py", "Adds CSP nonce and response security headers; redirects users lacking TOTP to enrollment and requires recent MFA for protected admin access."),
    ("ContributionSystem/context_processors.py", "Provides common school-role and access flags plus configured Umami values and current named route."),
    ("ContributionSystem/notifications.py", "Creates PDF audit summaries, snapshots model fields/relationships, and emails record changes. Also notifies active staff email recipients of account recovery requests; delivery failures are logged and surfaced without discarding the saved request."),
    ("ContributionSystem/admin.py", "School admin branding; account recovery review queue; model registrations. RecordAuditAdminMixin assigns creator attribution, blocks unsafe bulk deletion, gates delete reauthentication, and sends audit notifications."),
    ("ContributionSystem/urls.py", "Named routes for profiles, recovery/deletion, home, parent/student CRUD, clothing/supply history, collections, supplies, logout, i18n, and allauth."),
    ("ContributionSystem/views.py", "Views for profile/account/home and record workflows. Shared deletion helper handles confirmation and protected-record conflicts. Role checks guard record CRUD/search; collections filter categories; supply entry is transactional; clothing actions record verification metadata."),
    ("ContributionSystem/tests.py", "Django TestCase suite and MFA test helper. Covers search/HTMX, forms, supply/clothing operations, delete confirmations, MFA, audit notifications, role access, language/social sign-in, CSP, account flows, and profiles."),
]:
    file(path, desc)
subsection("ContributionSystem migration history")
for path, desc in [
    ("ContributionSystem/migrations/__init__.py", "Migration package marker."),
    ("ContributionSystem/migrations/0001_initial.py", "Creates initial parents, students, collections, and their relationships."),
    ("ContributionSystem/migrations/0002_storesupplyreceipt_studentclothingverification.py", "Adds supply receipts and clothing-verification tables."),
    ("ContributionSystem/migrations/0003_storesupplyreceipt_student.py", "Adds optional protected student reference to a supply receipt."),
    ("ContributionSystem/migrations/0004_parent_created_by.py", "Adds parent creator attribution."),
    ("ContributionSystem/migrations/0005_access_roles.py", "Idempotently creates predefined school role groups."),
    ("ContributionSystem/migrations/0006_accountrecoveryrequest.py", "Creates the administrator-reviewed recovery request table."),
]:
    file(path, desc)

section("6. LibraryManagement files")
for path, desc in [
    ("LibraryManagement/__init__.py", "Python package marker."),
    ("LibraryManagement/apps.py", "Registers the library app."),
    ("LibraryManagement/models.py", "Book is a catalog title; available_copies subtracts active loans. BookLoan stores student/title, physical book_number, issue/due/return dates, and issuing user. Conditional constraints protect active loans; is_overdue ignores returned loans."),
    ("LibraryManagement/forms.py", "BookForm normalizes blank ISBN. BookLoanForm filters available titles, orders students, defaults due date to 14 days, requires a copy number, and validates active copy-number duplication."),
    ("LibraryManagement/access.py", "Library access policy/decorator: anonymous users go to sign-in; authenticated users without library permissions receive forbidden access."),
    ("LibraryManagement/context_processors.py", "Adds can_manage_library to template context for conditional navigation."),
    ("LibraryManagement/views.py", "Dashboard/search/filter; book CRUD preserving loan history; transactional/locked issue checks for stock and duplicate loans; POST-only return checks submitted physical copy number before setting returned_at."),
    ("LibraryManagement/urls.py", "Namespaced dashboard, book add/edit/delete, loan list/issue, and POST return routes."),
    ("LibraryManagement/admin.py", "Book and loan administration with filters/search, copy number display, autocomplete, and read-only issue/return times."),
    ("LibraryManagement/tests.py", "Covers library access, issue/return, matching copy IDs, duplicate active IDs, page/template rendering, catalog creation, and unavailable stock."),
    ("LibraryManagement/migrations/__init__.py", "Migration package marker."),
    ("LibraryManagement/migrations/0001_initial.py", "Creates Book and BookLoan plus loan indexes and active title/student uniqueness."),
    ("LibraryManagement/migrations/0002_bookloan_book_number_and_more.py", "Adds nullable/blank physical copy number and active title/copy uniqueness; legacy loans remain supported."),
]:
    file(path, desc)

section("7. URL-to-template map: portal and records")
for path, desc in [
    ("templates/contributions/base.html", "Main portal shell: shared responsive style, navigation, theme/language controls, status messages, and feedback scripts."),
    ("templates/home.html", "Public landing page and signed-in role-dependent shortcuts; includes sign-in and recovery entry points."),
    ("templates/partials/user_greeting_clock.html", "Reusable greeting and live-clock markup."),
    ("templates/admin/base_site.html", "Django admin branding and conditional library shortcut."),
    ("templates/contributions/parent_list.html", "Parent search/create screen with HTMX result target."),
    ("templates/contributions/partials/parent_results.html", "Parent result rows, empty/search states, and allowed row action."),
    ("templates/contributions/student_list.html", "Student search/registration screen with HTMX result target."),
    ("templates/contributions/partials/student_results.html", "Student result rows and permitted clothing/supply/edit/delete links."),
    ("templates/contributions/student_form.html", "Student registration/edit form grouped by student, parent, and address."),
    ("templates/contributions/student_clothing.html", "Clothing verification form, existing checks, edit/delete actions."),
    ("templates/contributions/collection_list.html", "Collection search/add page and dynamic results region."),
    ("templates/contributions/partials/collection_results.html", "Collection rows, empty/search state, and record actions."),
    ("templates/contributions/form.html", "Configurable record form with instructions, prerequisites, and repeatable supply-item rows."),
    ("templates/contributions/supply_list.html", "Supply receipt search/add page with dynamic result target."),
    ("templates/contributions/partials/supply_results.html", "Supply rows and student history/edit/delete actions."),
    ("templates/contributions/student_supply_history.html", "Student supply totals and dated receipt history."),
    ("templates/contributions/partials/form_field.html", "Reusable labeled input, required marker, help text, and field errors."),
    ("templates/contributions/confirm_delete.html", "Explicit record deletion confirmation and blocked-deletion warning."),
]:
    file(path, desc)

section("8. URL-to-template map: library and accounts")
for path, desc in [
    ("templates/librarymanagement/base.html", "Library frame: catalog/loans navigation, theme toggle, messages, stylesheet, shared feedback script."),
    ("templates/librarymanagement/dashboard.html", "Inventory and loan statistics, catalog filters/actions, recent activity."),
    ("templates/librarymanagement/book_form.html", "Catalog title add/edit form."),
    ("templates/librarymanagement/book_confirm_delete.html", "Book deletion confirmation and warning when loan history prevents deletion."),
    ("templates/librarymanagement/loan_form.html", "Issue form for title, student, copy number, and due date."),
    ("templates/librarymanagement/loan_list.html", "Loan filters/search/table; displays copy ID and asks for it before returning numbered copies."),
    ("templates/accounts/profile.html", "Account summary and email/password/MFA/deletion links."),
    ("templates/accounts/profile_edit.html", "Username/name editing; verified email changes remain separate."),
    ("templates/accounts/recovery.html", "Password-reset/recovery-code advice and human-review request form."),
    ("templates/accounts/recovery_submitted.html", "Generic request acknowledgement and identity-verification instructions."),
    ("templates/accounts/confirm_delete.html", "Permanent account deletion warning and explicit checkbox form; view enforces MFA."),
    ("templates/account/login.html", "allauth sign-in override retaining configured passkey/code/social controls and linking to recovery."),
    ("templates/account/email.html", "allauth email-management actions: add, verify, primary selection, and removal."),
    ("templates/allauth/layouts/base.html", "Shared allauth shell: portal styling/nav, theme, messages, account menu, greeting, clock, and scripts."),
    ("templates/mfa/recovery_codes/index.html", "allauth recovery code display/download/regeneration override."),
    ("templates/mfa/webauthn/snippets/scripts.html", "Nonce-aware WebAuthn script tags and no-JavaScript notice."),
]:
    file(path, desc)

section("9. Static assets and localization")
for path, desc in [
    ("static/css/user-greeting.css", "Greeting, clock, and role-access notice styles."),
    ("static/librarymanagement/library.css", "Responsive library catalog/forms/table styles and light/dark theme tokens."),
    ("static/js/ui-feedback.js", "Loads/persists kafunjo-theme, updates accessible theme control, and manages progress indicators for navigation/forms/HTMX."),
    ("static/js/live-clock.js", "Formats and refreshes live-clock elements using browser date/time formatting."),
    ("static/js/supply-items.js", "Adds/removes repeatable Django supply formset rows and synchronizes the form count."),
    ("static/js/umami-pageview.js", "Sends named page views when Umami tracker metadata is configured."),
    ("static/vendor/htmx.min.js", "Third-party minified HTMX fragment-request library; not first-party business logic."),
    ("static/vendor/HTMX-LICENSE.txt", "License notice for vendored HTMX."),
    ("static/.gitkeep", "Keeps the static folder present in version control."),
    ("locale/sw/LC_MESSAGES/django.po", "Swahili gettext catalog: msgid/msgstr translation pairs for portal UI."),
]:
    file(path, desc)

section("10. How important workflows work")
subsection("Issue and return a physical library copy")
paragraph(
    "The issue form selects a title with available stock and a student, then "
    "requires the number printed on the physical copy, such as 01/100. On POST, "
    "the view locks the selected book and recalculates active loans. It checks "
    "stock, duplicate active copy numbers, and an existing active loan of the "
    "same title by that student before saving issued_by. The loan list displays "
    "the number. A return POST must send the matching number; a mismatch leaves "
    "returned_at unset and reports an error."
)
subsection("Create and delete school records")
paragraph(
    "A named route enters a view wrapped with login/role checks. A form validates "
    "input; a successful save records attribution and redirects with a message. "
    "Record deletion uses a confirmation page, a transaction, and database "
    "protected-relationship handling. Relevant tests cover valid and blocked cases."
)
subsection("Recover and delete accounts")
paragraph(
    "Lost-all-factor recovery submits a pending request for administrator review "
    "without revealing account existence or resetting MFA. Active staff with "
    "email addresses are notified; notification failures do not remove the "
    "request and trigger a user-facing warning. Account deletion from the profile "
    "requires recent MFA plus a required confirmation checkbox. Afterward the "
    "session is logged out and the user is deleted; school history follows each "
    "relationship's SET_NULL/PROTECT behavior."
)

section("11. Database changes and commands")
paragraph(
    "A migration is the versioned schema history. Change the model, generate and "
    "review a migration, then apply it. Never manually edit SQLite or rewrite an "
    "already-applied migration to repair a local schema."
)
code(
    "Common Windows PowerShell commands",
    "python manage.py check\n"
    "python manage.py makemigrations --check --dry-run\n"
    "python manage.py migrate\n"
    "python manage.py test\n"
    "python manage.py test ContributionSystem.tests\n"
    "python manage.py test LibraryManagement.tests\n"
    "python manage.py runserver",
)
paragraph(
    "Activate the project's selected virtual environment first if required. "
    "Django tests use an isolated test database; do not direct test runs at "
    "production data."
)
subsection("Test coverage map")
paragraph(
    "ContributionSystem.tests.py covers HTMX and normal list rendering, form "
    "validation, supply/clothing workflows, deletion confirmations, role access, "
    "MFA enrollment/reauthentication, audit emails/PDFs, language/social sign-in, "
    "CSP nonces, and account recovery/deletion. LibraryManagement.tests.py covers "
    "staff permissions, inventory/loan rules, copy number matching, duplicate "
    "copy prevention, templates, catalog creation, and unavailable stock."
)
subsection("A reliable feature-change loop")
code(
    "Model-backed feature workflow",
    "1. Update model and relationship/constraint rules.\n"
    "2. Generate and review migrations.\n"
    "3. Update form validation, views, and admin display.\n"
    "4. Update the directly related template and translations.\n"
    "5. Add focused success and failure tests.\n"
    "6. Run targeted tests, system checks, and broader tests.",
)

section("12. How to extend the project safely")
for item in [
    "Keep school-record work in ContributionSystem and circulation work in LibraryManagement.",
    "Enforce permissions in views; hiding a template link is not authorization.",
    "Use POST and CSRF for state changes and the existing confirmation pattern for destructive actions.",
    "Keep database invariants in constraints and view validation; use transactions/locks for race-prone stock checks.",
    "Create migrations for model changes and verify them on a clean test database.",
    "Use gettext helpers and template translation tags for user-facing text.",
    "Use request.csp_nonce for inline script/style and avoid weakening CSP.",
    "Keep secrets out of source, PDFs, logs, and support messages.",
    "Update the relevant admin, template, and focused tests with model/form/view changes.",
]:
    paragraph("• " + item)

section("13. Scope and repository notes")
paragraph(
    "The maintained application inventory comprises 41 Python files (including "
    "migrations), 34 HTML templates, configuration examples, tests, translations, "
    "notices, and first-party assets. The guide gives individual file descriptions "
    "for application modules, migrations, and templates."
)
paragraph(
    "The checkout also contains generated bytecode/cache files and a local SQLite "
    "database. These are not source-code blocks and are not reproduced here. A "
    "machine-generated connectivity report is excluded because it describes the "
    "developer environment. The private .env is not read or documented."
)
paragraph(
    "main.py is empty; manage.py is the actual Django command entry point. "
    ".gitignore excludes local/generated material but cannot untrack files that "
    "were committed previously. Treat the SQLite file as operational data and "
    "confirm its source-control status against school data policy."
)
subsection("Glossary")
for item in [
    "Model — Python class describing persisted fields, relationships, and constraints.",
    "Migration — versioned database schema operation generated from model changes.",
    "View — request handler that authorizes, validates, reads/writes data, and responds.",
    "Form — parses and validates user input, often directly into a model.",
    "Template — HTML presentation rendered from context and template tags.",
    "Middleware — cross-cutting request/response behavior, such as security headers.",
    "Context processor — supplies common template values to many pages.",
    "HTMX partial — HTML fragment returned to update one portion of a page.",
    "MFA — multi-factor authentication; used here to gate sensitive actions.",
]:
    paragraph(item)

GuideDocument(str(DESTINATION)).multiBuild(story)
print(f"Created {DESTINATION} ({DESTINATION.stat().st_size:,} bytes)")
