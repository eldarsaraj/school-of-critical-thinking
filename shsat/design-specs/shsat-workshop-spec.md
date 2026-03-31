# The SHSAT Workshop — Product Specification

**Project:** The School of Critical Thinking
**URL:** schoolofcriticalthinking.org/shsat/
**Status:** Pre-development — approved concept
**Stack:** Django (existing project), PostgreSQL, Stripe, Claude API, Chart.js

---

## 1. Product overview

The SHSAT Workshop is an online preparation platform for New York City's Specialized High Schools Admissions Test. It lives as a subdirectory of schoolofcriticalthinking.org, inside the existing Django project as a new app called `shsat`.

It combines timed practice tests that simulate the real digital SHSAT with a parent-facing analytics dashboard that tracks progress, identifies skill gaps, predicts school placement, and recommends what to study next.

**Tagline:** Systematic preparation for New York's Specialized High Schools.

---

## 2. Users and accounts

### Account model

One account type: **parent**. The parent creates an account with their email address, a password, their child's first name or nickname (no real/full names required), and the child's current grade level (6, 7, or 8). The parent manages everything — there is no separate student login.

The parent hands the computer to the child when it's time to take a test. The parent reviews the dashboard and results afterward.

### Authentication

Use Django's built-in `auth` system. Login is email + password (not username). The `Parent` model extends Django's `AbstractUser` or uses a one-to-one profile linked to `User`.

### Registration fields

- Email address (used as username)
- Password (with confirmation)
- Child's first name or nickname
- Child's current grade (choices: 6, 7, 8)
- Checkbox: agreement to Terms of Service and Privacy Policy

### Privacy requirements

This platform stores children's test performance data. The following rules apply:

- No child's real/full name is ever required. A first name or nickname is sufficient.
- No child data is shared with third parties, ever.
- No tracking pixels, analytics cookies, or third-party scripts beyond Stripe (for payment).
- The privacy policy must be written, linked from the registration page, and accessible from the footer.
- COPPA: since the account holder is the parent (an adult) and the platform does not collect information directly from children or allow children to create accounts, the platform operates under parental consent by design. However, the privacy policy should explicitly state that the service is intended for parents and that children's test data is stored solely for the parent's use.
- Parents can delete their account and all associated data at any time from account settings. Deletion is permanent and immediate.
- Data stored: email, hashed password, child nickname, child grade, test attempts, answers, scores. No IP logging beyond what Django/the web server does by default.

---

## 3. Information architecture

### URL structure

All URLs live under `/shsat/` within the existing Django project.

```
/shsat/                          → Landing page (public, unauthenticated)
/shsat/signup/                   → Account creation
/shsat/login/                    → Login
/shsat/logout/                   → Logout (POST)
/shsat/dashboard/                → Parent dashboard (requires login)
/shsat/dashboard/log-score/      → Manual score entry form
/shsat/tests/                    → List of available tests (requires login)
/shsat/test/<id>/                → Pre-test screen (instructions, start button)
/shsat/test/<id>/take/           → Test-taking interface (timed)
/shsat/test/<id>/results/        → Test results and analysis
/shsat/resources/                → Curated prep resources (public)
/shsat/subscribe/                → Stripe Checkout redirect (requires login)
/shsat/subscription/manage/      → Cancel/manage subscription
/shsat/account/                  → Account settings (change password, delete account)
/shsat/account/delete/           → Account deletion confirmation
/shsat/privacy/                  → Privacy policy
/shsat/terms/                    → Terms of service
/shsat/webhook/stripe/           → Stripe webhook endpoint (no UI)
```

### Navigation

The site header gains a new nav link: **SHSAT Prep** (or **Workshop**), linking to `/shsat/`. This appears in the main `site-nav` alongside About, Curriculum, Books, Articles.

Within the SHSAT section, a secondary tab bar appears below the page title with three tabs:

- **Dashboard** → `/shsat/dashboard/`
- **Practice Tests** → `/shsat/tests/`
- **Resources** → `/shsat/resources/`

The tab bar uses the same styling as the prototype: uppercase 13px labels, 0.06em letter-spacing, 2px bottom border on active tab.

---

## 4. Django app structure

### App name: `shsat`

```
shsat/
├── __init__.py
├── admin.py              # Admin interface for managing tests, questions, scores
├── apps.py
├── forms.py              # Registration, login, manual score entry, etc.
├── models.py             # All models (see section 5)
├── urls.py               # URL routing
├── views.py              # View functions or class-based views
├── scoring.py            # Score calculation, scaling, placement prediction logic
├── ai_questions.py       # Claude API integration for question generation
├── stripe_utils.py       # Stripe checkout, webhook handling, subscription management
├── templatetags/
│   └── shsat_tags.py     # Custom template tags (e.g., percentage formatting)
├── templates/
│   └── shsat/
│       ├── base_shsat.html       # Extends site base.html, adds tab bar
│       ├── landing.html          # Public landing page
│       ├── signup.html           # Registration form
│       ├── login.html            # Login form
│       ├── dashboard.html        # Parent dashboard
│       ├── log_score.html        # Manual score entry
│       ├── test_list.html        # Available tests
│       ├── test_intro.html       # Pre-test instructions
│       ├── test_take.html        # Test-taking interface
│       ├── test_results.html     # Results and analysis
│       ├── resources.html        # Prep resources
│       ├── subscribe.html        # Subscription prompt
│       ├── account.html          # Account settings
│       ├── privacy.html          # Privacy policy
│       └── terms.html            # Terms of service
├── static/
│   └── shsat/
│       ├── css/
│       │   └── shsat.css         # Additional styles specific to SHSAT app
│       └── js/
│           ├── test-timer.js     # Timer logic (countdown + overtime)
│           ├── test-interface.js # Question navigation, flagging, answer selection
│           └── dashboard.js      # Chart.js initialization, interactive elements
├── management/
│   └── commands/
│       ├── generate_questions.py # Management command to batch-generate AI questions
│       └── import_doe_test.py    # Management command to import DOE test data
├── migrations/
└── tests.py
```

### Settings additions

Add to the existing Django project's `settings.py`:

```python
INSTALLED_APPS += ['shsat']

# Stripe
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET')
STRIPE_PRICE_ID = env('STRIPE_PRICE_ID')  # The $24.99/month price object

# Anthropic (for AI question generation)
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY')

# SHSAT-specific
SHSAT_FREE_TEST_LIMIT = 1  # Number of free tests before subscription required
SHSAT_TEST_DURATION_SECONDS = 10800  # 3 hours = 10,800 seconds
```

### URL inclusion

In the project's root `urls.py`:

```python
urlpatterns += [
    path('shsat/', include('shsat.urls')),
]
```

---

## 5. Data models

### Parent

```python
class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shsat_parent')
    child_nickname = models.CharField(max_length=50)
    child_grade = models.IntegerField(choices=[(6, '6th'), (7, '7th'), (8, '8th')])
    
    # Stripe
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Free'),
            ('active', 'Active'),
            ('canceled', 'Canceled'),
            ('past_due', 'Past Due'),
        ],
        default='free'
    )
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    
    # Target schools (parent selects which schools to track on dashboard)
    target_schools = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def has_active_subscription(self):
        return self.subscription_status == 'active'
    
    def tests_taken_count(self):
        return self.test_attempts.filter(is_completed=True).count()
    
    def can_take_test(self):
        if self.has_active_subscription():
            return True
        return self.tests_taken_count() < settings.SHSAT_FREE_TEST_LIMIT
```

### Test

```python
class Test(models.Model):
    title = models.CharField(max_length=200)  # e.g., "Practice Test 1 — DOE 2023 Form A"
    description = models.TextField(blank=True)
    source = models.CharField(
        max_length=20,
        choices=[
            ('doe', 'DOE Official'),
            ('original', 'Original'),
            ('ai', 'AI-Generated'),
        ]
    )
    is_free = models.BooleanField(default=False)  # The one free diagnostic test
    is_published = models.BooleanField(default=False)  # Draft vs live
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0)  # Display ordering
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def question_count(self):
        return self.questions.count()
    
    def ela_questions(self):
        return self.questions.filter(section='ela')
    
    def math_questions(self):
        return self.questions.filter(section='math')
```

### Question

```python
class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    
    # Position and section
    section = models.CharField(max_length=4, choices=[('ela', 'ELA'), ('math', 'Math')])
    question_number = models.IntegerField()  # 1-57 within each section
    
    # Question type
    question_type = models.CharField(
        max_length=20,
        choices=[
            ('multiple_choice', 'Multiple Choice'),
            ('grid_in', 'Grid-In'),
        ]
    )
    
    # Topic tagging (for analytics)
    topic = models.CharField(
        max_length=40,
        choices=[
            # ELA topics
            ('revising_editing', 'Revising / Editing'),
            ('reading_comp_fiction', 'Reading Comprehension — Fiction'),
            ('reading_comp_nonfiction', 'Reading Comprehension — Nonfiction'),
            ('reading_comp_poetry', 'Reading Comprehension — Poetry'),
            # Math topics
            ('numbers_operations', 'Numbers and Operations'),
            ('algebra', 'Algebra'),
            ('geometry', 'Geometry and Measurement'),
            ('probability_statistics', 'Probability and Statistics'),
            ('word_problems', 'Word Problems'),
        ]
    )
    
    difficulty = models.CharField(
        max_length=10,
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
        default='medium'
    )
    
    # Content
    passage_text = models.TextField(blank=True)  # For reading comp questions; shared across a group
    passage_title = models.CharField(max_length=200, blank=True)
    question_text = models.TextField()
    
    # Choices (for multiple choice)
    choice_a = models.TextField(blank=True)
    choice_b = models.TextField(blank=True)
    choice_c = models.TextField(blank=True)
    choice_d = models.TextField(blank=True)
    
    # Answer
    correct_answer = models.CharField(max_length=10)  # 'a', 'b', 'c', 'd' or a numeric string for grid-in
    explanation = models.TextField(blank=True)  # Shown in results
    
    # Grouping: questions sharing a passage have the same passage_group_id
    passage_group_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['section', 'question_number']
        unique_together = ['test', 'section', 'question_number']
```

### TestAttempt

```python
class TestAttempt(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    # Which section the child started with
    started_with = models.CharField(
        max_length=4,
        choices=[('ela', 'ELA'), ('math', 'Math')],
        default='ela'
    )
    
    # Timing: total seconds spent (including overtime)
    total_seconds = models.IntegerField(null=True, blank=True)
    
    # Calculated scores (populated on submission)
    ela_correct = models.IntegerField(null=True, blank=True)
    ela_total = models.IntegerField(default=57)
    math_correct = models.IntegerField(null=True, blank=True)
    math_total = models.IntegerField(default=57)
    
    # Estimated scaled scores
    ela_scaled = models.IntegerField(null=True, blank=True)
    math_scaled = models.IntegerField(null=True, blank=True)
    composite_score = models.IntegerField(null=True, blank=True)
    
    # Parent notes (optional, added after reviewing results)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def overall_correct(self):
        if self.ela_correct is not None and self.math_correct is not None:
            return self.ela_correct + self.math_correct
        return None
    
    def overall_total(self):
        return self.ela_total + self.math_total
    
    def overall_percentage(self):
        total = self.overall_correct()
        if total is not None:
            return round(total / self.overall_total() * 100)
        return None
    
    def was_overtime(self):
        if self.total_seconds is not None:
            return self.total_seconds > settings.SHSAT_TEST_DURATION_SECONDS
        return False
    
    def overtime_seconds(self):
        if self.was_overtime():
            return self.total_seconds - settings.SHSAT_TEST_DURATION_SECONDS
        return 0
```

### Answer

```python
class Answer(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    selected_answer = models.CharField(max_length=10, blank=True)  # 'a','b','c','d' or numeric for grid-in
    is_correct = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)  # Was flagged for review during test
    
    class Meta:
        unique_together = ['attempt', 'question']
```

### ManualScore

```python
class ManualScore(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='manual_scores')
    
    date = models.DateField()
    source_name = models.CharField(max_length=200)  # e.g., "Kaplan Test 1", "Tutorverse Mock 3"
    ela_correct = models.IntegerField()
    ela_total = models.IntegerField(default=57)
    math_correct = models.IntegerField()
    math_total = models.IntegerField(default=57)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
    
    def overall_correct(self):
        return self.ela_correct + self.math_correct
    
    def overall_total(self):
        return self.ela_total + self.math_total
    
    def overall_percentage(self):
        return round(self.overall_correct() / self.overall_total() * 100)
```

### CutoffScore

```python
class CutoffScore(models.Model):
    """
    Stores historical and current cutoff scores for each specialized high school.
    Updated annually when DOE releases new data.
    """
    school_name = models.CharField(max_length=100)
    school_short = models.CharField(max_length=30)  # e.g., "Stuyvesant", "Bronx Sci"
    admissions_year = models.IntegerField()  # e.g., 2026
    cutoff_score = models.IntegerField()
    approximate_seats = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-admissions_year', '-cutoff_score']
        unique_together = ['school_name', 'admissions_year']
```

---

## 6. Page specifications

### 6.1 Landing page (`/shsat/`)

**Public. No login required.**

Purpose: explain the product and convert visitors to sign-ups.

Content (in order):

1. **Page title:** "The SHSAT Workshop"
2. **Subtitle:** "Systematic preparation for New York's Specialized High Schools."
3. **Section: "What this is"** — 2–3 paragraphs explaining the platform: timed practice tests that simulate the real digital SHSAT, a dashboard that tracks progress and predicts school placement, and a structured approach to preparation. Tone matches the rest of the site — serious, calm, no hype.
4. **Section: "What you get"** — list of features:
   - Full-length timed practice tests (114 questions, 3 hours)
   - Score tracking dashboard with progress charts
   - Topic-level breakdown of strengths and weaknesses
   - School placement prediction based on latest cutoff data
   - Recommended study plan after each test
   - Manual score logging for tests taken elsewhere
5. **Section: "How it works"** — 3 steps: Create a free account → Your child takes the diagnostic test → See where they stand and what to improve.
6. **Section: "Pricing"** — Free: dashboard + 1 complete practice test. Workshop membership: $24.99/month for unlimited tests. Cancel anytime.
7. **CTA:** "Create your free account" → links to `/shsat/signup/`
8. **Section: "About"** — brief note that this is built by The School of Critical Thinking. Link to the main About page.

Design: follows site conventions exactly. Sections separated by 0.5px borders with uppercase kicker labels. CTA button uses the site's standard text-button style (no background, uppercase, underline on bottom).

### 6.2 Registration (`/shsat/signup/`)

**Public.**

Fields:
- Email address (text input)
- Password (password input)
- Confirm password (password input)
- Child's first name or nickname (text input, max 50 chars)
- Child's grade (select: 6th, 7th, 8th)
- Checkbox: "I agree to the Terms of Service and Privacy Policy" (links open in new tab)

Submit button: "Create account" (site's standard text-button style).

On success: redirect to `/shsat/dashboard/` with a welcome message.

Validation: Django form validation. Email must be unique. Password must meet Django's default validators. All fields required.

Form styling: matches the existing contact form on the site exactly (`contact-form__field` pattern — label above, full-width input, 1px border, no border-radius, rgba backgrounds).

### 6.3 Login (`/shsat/login/`)

**Public.**

Fields: email, password.
Link: "Don't have an account? Sign up" → `/shsat/signup/`
Link: "Forgot password?" → Django's password reset flow.

### 6.4 Dashboard (`/shsat/dashboard/`)

**Requires login.**

This is the parent's home screen. It displays data from both platform test attempts and manually logged scores, merged chronologically.

#### Section: "Current standing"

Four stat cards in a row:

| Card | Label | Value | Subtext |
|------|-------|-------|---------|
| Latest score | `LATEST SCORE` | Overall percentage from most recent test/score | "X / Y correct" |
| ELA | `ELA` | ELA percentage from most recent test | "X / 57 correct" |
| Math | `MATH` | Math percentage from most recent test | "X / 57 correct" |
| Tests taken | `TESTS TAKEN` | Count of completed platform tests + manual scores | "Since [earliest date]" |

If no tests have been taken yet, show a prompt: "No test data yet. Take your first practice test to see your dashboard." with a link to `/shsat/tests/`.

#### Section: "Score progression"

A Chart.js line chart showing percentage scores over time. X-axis: test dates. Y-axis: 0–100%.

Three lines:
- **Overall %** — solid, rgba(0,0,0,0.7), 2px
- **ELA %** — dashed, rgba(0,0,0,0.35), 1.5px
- **Math %** — dotted, rgba(0,0,0,0.22), 1.5px

Horizontal dashed target lines for each school the parent has selected as a target (stored in `Parent.target_schools`). Default targets if none selected: Bronx Science (~85%) and Brooklyn Tech (~75%).

Chart.js configuration: responsive, no built-in legend (custom HTML legend above the chart), rgba black grid lines, Helvetica font, no border on axes.

Data includes both platform test attempts and manual scores, merged by date.

#### Section: "School placement"

A table showing all 8 specialized high schools with:
- School name
- Most recent cutoff score (from `CutoffScore` model, latest admissions year)
- Approximate seats
- Status indicator based on child's latest composite score estimate:
  - **Admitted** (score ≥ cutoff): shown in regular text
  - **Within reach** (score within 20 points below cutoff): shown with a subtle indicator
  - **Not yet competitive** (score more than 20 points below): shown in muted text

If no test has been taken yet, show cutoff data without status indicators.

#### Section: "Mock test history"

A table with columns: #, Date, Source, ELA, Math, Overall %, Time, Notes.

Rows include both platform test attempts and manual scores, sorted by date descending. Platform tests show actual timing data; manual scores show "—" for time. Overtime is displayed in red (e.g., "3h 12m" where "12m" portion is red, or the whole time value is red with a note).

A link at the top right: "Log an external score →" linking to `/shsat/dashboard/log-score/`.

#### Section: "Target schools" (small settings area)

A simple form where the parent can check/uncheck which schools to track as targets on the dashboard. Defaults to Bronx Science and Brooklyn Tech. This updates `Parent.target_schools`.

### 6.5 Manual score entry (`/shsat/dashboard/log-score/`)

**Requires login.**

A simple form for logging scores from tests taken outside the platform (Kaplan, Tutorverse, DOE tests on paper, etc.).

Fields:
- Date (date picker)
- Test source name (text input, e.g., "Kaplan Test 1")
- ELA questions correct (number input, 0–57)
- ELA total questions (number input, default 57, editable in case of partial tests)
- Math questions correct (number input, 0–57)
- Math total questions (number input, default 57)
- Notes (textarea, optional)

Submit: "Log score" (text-button style).

On success: redirect back to dashboard with the new score visible in the chart and history.

### 6.6 Test list (`/shsat/tests/`)

**Requires login.**

Shows all published tests, sorted by `order` field.

Each test is displayed as a row/card with:
- Test title
- Source label (DOE Official / Original / AI-Generated)
- Question count (should always be 114)
- Status: "Available" (can take), "Completed" (already taken, with score shown), or "Locked" (requires subscription)

Lock logic:
- If the test's `is_free` is True → always available.
- If the parent has an active subscription → all tests available.
- Otherwise → locked. Show a prompt: "Unlock all practice tests — $24.99/month" linking to `/shsat/subscribe/`.

A completed test shows the overall percentage and a "View results →" link.

### 6.7 Pre-test screen (`/shsat/test/<id>/`)

**Requires login. Test must be available (not locked).**

Content:
1. Test title and source
2. Instructions:
   - "This test has 57 ELA questions and 57 Math questions."
   - "The standard time is 3 hours (180 minutes). A timer will count down from 3:00:00."
   - "If you go over 3 hours, the timer will continue counting up in red so you can see how much extra time was used."
   - "You may start with either ELA or Math."
   - "You can flag questions for review and return to them before submitting."
   - "There is no penalty for wrong answers. Answer every question."
3. Section choice: two buttons — "Start with ELA" and "Start with Math"

Clicking either button creates a new `TestAttempt` record with `started_with` set accordingly and redirects to the test-taking interface.

### 6.8 Test-taking interface (`/shsat/test/<id>/take/`)

**Requires login. Active test attempt must exist.**

This is the core product screen. It must feel focused and distraction-free while providing all the navigation tools the real SHSAT offers.

#### Layout

- **Top bar (fixed or sticky):** Section label (e.g., "English Language Arts — Revising / Editing"), timer, question counter ("Question 3 of 57").
- **Question map:** A grid of 57 numbered squares for the current section. Shows current question (darker border), answered questions (subtle fill), flagged questions (warm-toned border). Clicking a square navigates to that question.
- **Content area:** Passage text (if applicable, in a bordered box) + question text + answer choices.
- **Bottom bar:** Flag button, Previous button, Next button. At the end of a section: "Switch to [other section]" button. After answering all questions in both sections: "Submit test" button.

#### Timer behavior

The timer starts at 3:00:00 and counts down. JavaScript-driven, updating every second.

**When the timer reaches 0:00:00:** The timer does NOT auto-submit the test. Instead, it switches to counting UP from 0:00:00, displayed in red. The label changes from the normal display to something like "Overtime: 0:01:23" in red text. The child can continue working. This overtime is recorded in `TestAttempt.total_seconds`.

This is the forgiving timing model. The parent can see on the dashboard exactly how much overtime was used, making pacing issues visible without cutting the child off mid-test.

The timer value is maintained via JavaScript `setInterval`. The start time is recorded server-side in `TestAttempt.started_at`. On submission, `total_seconds` is calculated as `(submitted_at - started_at).total_seconds()` server-side, so the timer is authoritative even if the browser tab is closed and reopened.

#### Answer persistence

Answers are saved to the server as the child selects them (AJAX POST on each answer selection). This prevents data loss if the browser crashes or the tab is accidentally closed. The child can return to `/shsat/test/<id>/take/` and resume where they left off as long as `is_completed` is False.

Implementation: each answer selection triggers a fetch() POST to a `/shsat/test/<id>/answer/` endpoint that creates or updates the `Answer` record. The response is silent (no page reload). Flag status is also saved via AJAX.

#### Section switching

The child starts with the section they chose on the pre-test screen. At the end of that section's questions, a "Continue to [Math/ELA]" button appears. They can also switch sections at any time via the section label or a toggle in the top bar.

The question map updates to show the current section's 57 questions. Both sections' question maps should be accessible (e.g., two rows of tabs labeled "ELA" and "Math" above the question grid).

#### Submission

A "Submit test" button is available once at least one answer has been given. On click, a confirmation dialog: "Are you sure you want to submit? You have X unanswered questions." On confirmation, a POST to the server that:

1. Sets `TestAttempt.is_completed = True` and `submitted_at = now()`
2. Calculates `total_seconds` from `started_at` to `submitted_at`
3. Counts correct answers for ELA and Math
4. Calculates estimated scaled scores (see scoring section)
5. Redirects to `/shsat/test/<id>/results/`

### 6.9 Test results (`/shsat/test/<id>/results/`)

**Requires login. Test must be completed.**

This is the high-value page that justifies the subscription. It shows comprehensive analysis of the completed test.

#### Section: "Score summary"

Stat cards showing:
- Overall: X / 114 correct (Y%)
- ELA: X / 57 correct (Y%)
- Math: X / 57 correct (Y%)
- Time: Xh Ym (if overtime, show "3h 00m + 12m overtime" with overtime portion in red)
- Estimated composite score: [scaled score] (with a note: "Estimated based on historical DOE scoring data. Actual SHSAT scaling varies by year.")

#### Section: "School placement prediction"

Same table format as the dashboard's school placement section, but specific to this test's composite score. Shows which schools the child would have been admitted to, which are within reach, and which are not yet competitive.

#### Section: "Topic breakdown"

A table showing performance by topic area:

| Topic | Correct | Total | Percentage | vs. Overall |
|-------|---------|-------|------------|-------------|
| Revising / Editing | 14 | 18 | 78% | ▼ below |
| Reading Comp — Fiction | 8 | 10 | 80% | — average |
| Reading Comp — Nonfiction | 12 | 15 | 80% | — average |
| Reading Comp — Poetry | 3 | 4 | 75% | ▼ below |
| Numbers and Operations | 10 | 11 | 91% | ▲ above |
| Algebra | 14 | 16 | 88% | ▲ above |
| Geometry | 7 | 12 | 58% | ▼▼ weak |
| Probability and Statistics | 5 | 6 | 83% | — average |
| Word Problems | 8 | 10 | 80% | — average |

The "vs. Overall" column compares each topic's percentage to the child's overall percentage. Topics more than 10% below overall are marked as weak areas.

#### Section: "Skill-gap analysis"

Plain-language paragraphs identifying the 2–3 most important areas to improve, based on the topic breakdown. This is generated server-side using simple logic:

1. Find topics where the percentage is more than 10% below the overall percentage.
2. Rank them by the absolute number of questions missed (more missed = higher priority).
3. Generate a sentence for each: "[Topic] is currently your weakest [math/ELA] area ([X]% correct vs. [Y]% overall). Focus on [specific sub-skill suggestions based on topic]."

The sub-skill suggestions are stored as a static mapping in `scoring.py` — for each topic, a list of concrete study actions. Example: geometry → "angle relationships, coordinate geometry, area and perimeter of composite shapes."

#### Section: "Recommended study plan"

A numbered list of 3–5 specific actions to take before the next test. Generated from the skill-gap analysis. Example:

1. Review comma splices and run-on sentences (revising/editing).
2. Practice 10 geometry problems focusing on angle relationships.
3. Read one poem and answer 4 comprehension questions.
4. Do 5 grid-in problems with fractions and decimals.

This is generated server-side with deterministic logic, not AI. The logic maps identified weak topics to specific study recommendations stored in a lookup table.

#### Section: "Question review"

A list of all 114 questions showing: question number, the child's answer, the correct answer, whether it was correct, and the question's topic tag. Incorrect answers are highlighted. Each question expands to show the full question text, passage (if applicable), all choices, and the explanation. This allows the parent and child to review every mistake — matching the approach described in the parent spreadsheet ("reviewed every wrong answer, explained why he got it wrong, explained why the correct answer is correct").

#### Section: "Notes"

A text area where the parent can add notes about this test attempt (e.g., "Started strong but lost focus in math section 40 minutes in"). Saved to `TestAttempt.notes` via AJAX or a simple form POST.

### 6.10 Resources (`/shsat/resources/`)

**Public. No login required.**

A curated page listing prep materials in recommended order. Content is hardcoded in the template (not database-driven). Organized into sections:

1. **Recommended preparation order** — phased list of books and test resources (Princeton Review → Barron's → Kaplan → Tutorverse → DOE tests)
2. **Free practice tests** — links to DOE released tests with notes on which have recycled questions
3. **Supplementary reading** — book recommendations for building ELA skills
4. **Online resources** — links to Greg's Tutoring, StuyPrep, Test Prep SHSAT, etc.

Design: matches the prototype's resource-item pattern — numbered phase labels, bold titles, muted descriptions.

### 6.11 Subscription (`/shsat/subscribe/`)

**Requires login.**

A page explaining the paid tier and initiating Stripe Checkout.

Content:
1. "Unlock all practice tests"
2. What's included: unlimited tests, full results, new tests added monthly
3. Price: $24.99/month, cancel anytime
4. Button: "Subscribe" → initiates Stripe Checkout session

#### Stripe integration

**Checkout flow:**

1. Parent clicks "Subscribe."
2. Django view creates a Stripe Checkout Session with:
   - `mode='subscription'`
   - `line_items` referencing the $24.99/month Stripe Price object
   - `customer_email` set to the parent's email
   - `success_url` = `/shsat/dashboard/?subscribed=1`
   - `cancel_url` = `/shsat/subscribe/?canceled=1`
   - `metadata` = `{'parent_id': parent.id}`
3. Redirect to Stripe's hosted checkout page.
4. On success, Stripe redirects back to the dashboard.

**Webhook handling (`/shsat/webhook/stripe/`):**

Listen for these Stripe events:

- `checkout.session.completed` → Set `Parent.subscription_status = 'active'`, store `stripe_customer_id`.
- `invoice.paid` → Confirm subscription is active, update `subscription_end_date`.
- `invoice.payment_failed` → Set `Parent.subscription_status = 'past_due'`.
- `customer.subscription.deleted` → Set `Parent.subscription_status = 'canceled'`.

The webhook endpoint must verify the Stripe signature using `STRIPE_WEBHOOK_SECRET`.

**Subscription management:**

At `/shsat/subscription/manage/`, the parent can:
- See their current subscription status and next billing date
- Cancel their subscription (via Stripe API call to cancel at period end)

After cancellation, the parent retains access until the end of the current billing period.

---

## 7. Scoring logic (`scoring.py`)

### Raw to scaled score conversion

The SHSAT uses a piecewise conversion from raw scores (0–57 per section) to scaled scores (~100–400 per section). The exact conversion changes yearly. The platform uses an approximation based on historical DOE data.

Store the conversion table as a Python dictionary mapping raw scores to scaled scores, one for ELA and one for Math. Default to the most recent available year's conversion. Update annually when new DOE data is published.

```python
# Approximate conversion (update annually with DOE data)
ELA_SCALE = {0: 100, 1: 103, 2: 107, ..., 47: 350, ..., 57: 400}
MATH_SCALE = {0: 100, 1: 103, 2: 107, ..., 47: 355, ..., 57: 400}

def raw_to_scaled(raw_correct, section):
    scale = ELA_SCALE if section == 'ela' else MATH_SCALE
    scored_correct = min(raw_correct, 47)  # Only 47 of 57 are scored
    return scale.get(scored_correct, 100)

def composite_score(ela_correct, math_correct):
    return raw_to_scaled(ela_correct, 'ela') + raw_to_scaled(math_correct, 'math')
```

Note: of the 57 questions per section, only 47 are scored (10 are unscored field-test items). Since the platform doesn't know which questions are unscored on the real test, score all 57 but note in the UI that the estimated score assumes all questions are scored, and actual SHSAT scoring may differ.

### School placement prediction

Compare the estimated composite score against the most recent `CutoffScore` entries. For each school:
- If composite ≥ cutoff: "Admitted"
- If composite ≥ cutoff - 20: "Within reach"
- If composite < cutoff - 20: "Not yet competitive"

### Percentile estimation

Initially, use historical DOE score distribution data to estimate percentile. The DOE reports that approximately 28,000 students take the SHSAT and roughly 5,000 receive offers. This gives a rough distribution curve. As the platform accumulates its own user data, switch to platform-specific percentiles.

---

## 8. AI question generation (`ai_questions.py`)

### Purpose

Generate original SHSAT-style questions using the Anthropic Claude API. Questions are generated in batches, reviewed by the founder in the Django admin, and published to tests.

### Generation workflow

1. Founder runs the management command: `python manage.py generate_questions --section ela --topic revising_editing --count 10`
2. The command calls the Claude API with a prompt specifying the section, topic, difficulty level, and SHSAT formatting conventions.
3. The API returns structured JSON with question text, passage (if applicable), choices, correct answer, and explanation.
4. The command creates `Question` objects with `test=None` (unassigned) and marks them as draft.
5. The founder reviews questions in Django admin, edits as needed, assigns them to a test, and publishes.

### Claude API prompt structure

The system prompt should include:
- A description of the SHSAT format and conventions for the specific section/topic
- Examples of real SHSAT-style questions (from DOE public tests, which are legal to reference)
- Specific instructions on difficulty level, answer choice plausibility, and explanation quality
- Output format: JSON with fields matching the Question model

The prompt should specify that all content must be original (not copied from any source) and appropriate for 8th-grade students.

### Management command

```
python manage.py generate_questions
    --section [ela|math]
    --topic [topic_choice]
    --difficulty [easy|medium|hard]
    --count [number of questions to generate]
    --passage  # If included, generate a passage with multiple questions
```

---

## 9. Design specification

The SHSAT Workshop inherits the School of Critical Thinking's design system completely. No new fonts, no new colors, no new patterns. The only additions are chart-specific styles and test-interface-specific styles.

### Inherited from site.css (do not duplicate, do not override)

- Background: `#FFFEF8` with dot texture (`radial-gradient(rgba(0,0,0,0.04) 1px, transparent 1px)`, `18px 18px`)
- Text: `color: #111` base; secondary text at various `rgba(0,0,0,...)` opacities
- Font: `Helvetica, Arial, sans-serif`
- Container: `max-width: 760px; margin: 0 auto`
- h1: `34px`, h2: `20px`, p: `18px / 1.7`
- Section labels (kickers): `11px`, `letter-spacing: 0.12em`, `text-transform: uppercase`, `rgba(0,0,0,0.55)`
- Section dividers: `0.5px solid rgba(0,0,0,0.08)`, with `margin-top: 48px+`, `padding-top: 18px`
- Cards: `border: 0.5px solid rgba(0,0,0,0.10)`, `border-radius: 10px`, `background: rgba(255,254,248,0.85)`
- Buttons: no background, `14px`, `letter-spacing: 0.06em`, `text-transform: uppercase`, `border-bottom: 1px solid rgba(0,0,0,0.35)`, `padding-bottom: 4px`
- Form inputs: `border: 1px solid rgba(0,0,0,0.18)`, `border-radius: 0`, `background: rgba(255,254,248,0.9)`
- Choice buttons (for test answers): match `.diagnostic__choice` exactly — `border: 1px solid rgba(0,0,0,0.14)`, `border-radius: 8px`, `background: rgba(255,254,248,0.92)`, same hover/active/selected states

### New styles in shsat.css

The `shsat.css` file contains ONLY styles that don't exist in `site.css`. Primarily:

- Tab bar (`.app-tabs`, `.app-tab`)
- Stat cards (`.stat-card`)
- Chart wrapper (`.chart-wrap`)
- Cutoff and log tables (`.cutoff-table`, `.log-table`)
- Test-taking interface (`.test-header`, `.test-timer`, `.q-map`, `.q-dot`, `.passage-box`, `.question-block`, `.flag-btn`)
- Timer overtime display (red color for overtime: `rgba(180,40,30,0.8)`)

All new styles must use `rgba(0,0,0,...)` for grays and borders, matching the existing palette. The only color that is not black-based is the overtime red: `rgba(180,40,30,0.8)`.

### Chart.js color scheme

Charts use the monochrome black palette only:
- Overall line: `rgba(0,0,0,0.7)`, solid, 2px
- ELA line: `rgba(0,0,0,0.35)`, dashed `[6,3]`, 1.5px
- Math line: `rgba(0,0,0,0.22)`, dotted `[2,3]`, 1.5px
- Target lines: `rgba(0,0,0,0.15)`, dashed `[4,4]`, 0.5px
- Grid: `rgba(0,0,0,0.04)`
- Axis text: `rgba(0,0,0,0.4)`, 11px Helvetica
- Point fills: `#FFFEF8` (paper background, so points have a "punched out" look)

### Template inheritance

```
base.html (existing site base)
  └── shsat/base_shsat.html (adds tab bar navigation + SHSAT-specific CSS/JS)
        ├── shsat/dashboard.html
        ├── shsat/test_list.html
        ├── shsat/test_take.html (might override more of the base for a cleaner test-taking layout)
        ├── shsat/test_results.html
        ├── shsat/resources.html
        ├── shsat/landing.html
        ├── shsat/signup.html
        ├── shsat/login.html
        └── ...
```

The `base_shsat.html` template:
- Extends `base.html`
- Adds `<link>` to `shsat/css/shsat.css`
- Adds the tab bar below the page title (Dashboard / Practice Tests / Resources)
- Includes `shsat/js/*.js` scripts as needed per page

---

## 10. Development phases

### Phase 1 — MVP (4–6 weeks)

**Goal:** A working product the founder can use with their daughter and share with 5–10 beta parents.

1. Create the `shsat` Django app with all models
2. Run migrations
3. Build registration, login, logout views and templates
4. Build the dashboard view with stat cards, progress chart, and test history
5. Build the manual score entry form
6. Build the test list page
7. Enter one complete test (114 questions) into the database via Django admin, using DOE public test content
8. Build the pre-test screen
9. Build the test-taking interface with timer, question map, answer selection, flagging, AJAX answer persistence
10. Build the submission flow and score calculation
11. Build the test results page with all sections (score summary, school placement, topic breakdown, skill gaps, study plan, question review)
12. Build the resources page
13. Seed the `CutoffScore` table with historical data
14. Write shsat.css
15. Test thoroughly with the founder's daughter

**Deliverable:** A working product at schoolofcriticalthinking.org/shsat/ with one free test, full dashboard, and full results. No payment processing yet.

### Phase 2 — Monetization (weeks 7–10)

1. Set up Stripe account and create the $24.99/month subscription product
2. Implement Stripe Checkout flow
3. Implement webhook handling
4. Implement test locking logic
5. Build subscription management page
6. Add 3–4 more tests (mix of DOE and AI-generated)
7. Build the landing page
8. Build the privacy policy and terms of service pages
9. Add account deletion functionality

**Deliverable:** A monetizable product with free and paid tiers.

### Phase 3 — Growth (months 3–6)

1. AI question generation pipeline (management command + Claude API)
2. Regular content updates (2 new tests per month)
3. Percentile ranking
4. Email capture and nurture sequences
5. SEO articles on the School's blog about SHSAT prep
6. Outreach in NYC parent communities

### Phase 4 — Advanced (months 6+)

1. Adaptive testing (CAT simulation)
2. Topic-specific drills
3. Multi-child profiles
4. Progress sharing with tutors
5. Integration with School's broader curriculum

---

## 11. Admin interface

Django admin should be configured for efficient test and question management:

### Test admin
- List display: title, source, is_free, is_published, question count, created_at
- Filters: source, is_free, is_published
- Actions: publish, unpublish

### Question admin
- List display: test, section, question_number, topic, difficulty, first 50 chars of question_text
- Filters: test, section, topic, difficulty
- Search: question_text
- Inline editing from the Test admin page (questions displayed as inlines)

### TestAttempt admin
- List display: parent, test, started_at, is_completed, ela_correct, math_correct, composite_score
- Filters: is_completed, test
- Read-only fields: answers (displayed inline)

### Parent admin
- List display: user email, child_nickname, child_grade, subscription_status, tests_taken_count, created_at
- Filters: subscription_status, child_grade

### CutoffScore admin
- List display: school_name, admissions_year, cutoff_score, approximate_seats

---

*This specification is implementation-ready. Every model, URL, page, and behavior is defined. Claude Code should be able to build the Phase 1 MVP from this document without further clarification.*
