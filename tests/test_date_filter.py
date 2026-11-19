import re

import pytest

import database.db as db

EMAIL = "demo@spendly.com"
PASSWORD = "demo123"

ALL_DESCS = ["Electricity bill", "Groceries", "Metro card", "Pharmacy"]


@pytest.fixture
def logged_in(client, app, add_expense):
    user_id = db.create_user("Demo User", EMAIL, PASSWORD)
    add_expense(user_id, 3200.00, "Bills", "2026-11-05", "Electricity bill")
    add_expense(user_id, 1850.50, "Food", "2026-11-03", "Groceries")
    add_expense(user_id, 500.00, "Transport", "2026-11-01", "Metro card")
    add_expense(user_id, 780.00, "Health", "2026-10-29", "Pharmacy")
    client.post("/login", data={"email": EMAIL, "password": PASSWORD})
    client.user_id = user_id
    return client


def html_of(client, query=""):
    response = client.get("/profile" + query)
    assert response.status_code == 200
    return response.data.decode()


def table_body(html):
    if "<tbody>" not in html:
        return ""
    return html.split("<tbody>")[1].split("</tbody>")[0]


def shown_descs(html):
    body = table_body(html)
    return [d for d in ALL_DESCS if d in body]


def row_count(html):
    return table_body(html).count("<tr>")


def stat_value(html, label):
    pattern = (
        r'profile-stat-label">\s*' + re.escape(label)
        + r'\s*</span>\s*<span class="profile-stat-value">\s*(.*?)\s*</span>'
    )
    return re.search(pattern, html, re.S).group(1)


def percents(html):
    return [
        float(p)
        for p in re.findall(r'profile-bar-percent">\s*([\d.]+)%', html)
    ]


class TestAuth:
    def test_logged_out_with_filter_redirects_to_login(self, client):
        response = client.get("/profile?start=2026-11-01&end=2026-11-05")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


class TestForm:
    def test_form_has_inputs_apply_and_clear(self, logged_in):
        html = html_of(logged_in)
        assert 'method="get"' in html
        assert 'type="date"' in html
        assert 'name="start"' in html
        assert 'name="end"' in html
        assert "Apply" in html
        assert "Clear" in html

    def test_form_prefilled_with_active_values(self, logged_in):
        html = html_of(logged_in, "?start=2026-11-01&end=2026-11-05")
        assert 'value="2026-11-01"' in html
        assert 'value="2026-11-05"' in html

    def test_clear_link_points_to_unfiltered_profile(self, logged_in):
        html = html_of(logged_in, "?start=2026-11-01")
        assert re.search(r'href="/profile"[^>]*>\s*Clear', html)

    def test_no_params_shows_all_rows_and_no_error(self, logged_in):
        html = html_of(logged_in)
        assert shown_descs(html) == ALL_DESCS
        assert 'role="alert"' not in html
        assert "Showing" not in html
        assert "Recent transactions" in html


class TestRange:
    def test_both_bounds_are_inclusive(self, logged_in):
        html = html_of(logged_in, "?start=2026-11-01&end=2026-11-05")
        assert shown_descs(html) == ["Electricity bill", "Groceries", "Metro card"]
        assert "5,550.50" in stat_value(html, "Total spent")
        assert stat_value(html, "Transactions") == "3"

    def test_single_day_range_on_bound_included(self, logged_in):
        html = html_of(logged_in, "?start=2026-11-05&end=2026-11-05")
        assert shown_descs(html) == ["Electricity bill"]
        assert stat_value(html, "Top category") == "Bills"

    def test_start_only_includes_on_or_after(self, logged_in):
        html = html_of(logged_in, "?start=2026-11-03")
        assert shown_descs(html) == ["Electricity bill", "Groceries"]
        assert "5,050.50" in stat_value(html, "Total spent")

    def test_end_only_includes_on_or_before(self, logged_in):
        html = html_of(logged_in, "?end=2026-11-01")
        assert shown_descs(html) == ["Metro card", "Pharmacy"]
        assert "1,280.00" in stat_value(html, "Total spent")

    def test_transactions_newest_first(self, logged_in):
        html = html_of(logged_in, "?start=2026-10-01&end=2026-11-30")
        body = table_body(html)
        positions = [body.index(d) for d in ALL_DESCS]
        assert positions == sorted(positions)

    def test_stats_top_category_reflects_range(self, logged_in):
        html = html_of(logged_in, "?start=2026-10-01&end=2026-11-02")
        assert stat_value(html, "Top category") in ("Health", "Transport")
        assert stat_value(html, "Transactions") == "2"

    def test_breakdown_only_covers_range(self, logged_in):
        html = html_of(logged_in, "?start=2026-11-03&end=2026-11-05")
        assert html.count('class="profile-bar-row"') == 2
        assert "profile-bar--health" not in html
        assert "profile-bar--transport" not in html

    def test_active_range_message_and_heading(self, logged_in):
        html = html_of(logged_in, "?start=2026-11-01&end=2026-11-05")
        assert "Showing" in html
        # The list is capped at 10 rows, so the heading stays "Recent".
        assert "Recent transactions" in html

    def test_amounts_use_rupee_not_dollar(self, logged_in):
        html = html_of(logged_in, "?start=2026-11-01&end=2026-11-05")
        assert "₹" in html
        assert "$" not in html

    def test_percentages_sum_to_100(self, logged_in):
        html = html_of(logged_in, "?start=2026-10-01&end=2026-11-30")
        pcts = percents(html)
        assert len(pcts) == 4
        assert sum(pcts) == pytest.approx(100, abs=0.01)

    def test_percentages_sum_to_100_for_awkward_split(self, logged_in, add_expense):
        # Three equal categories force rounding (33.33 x 3).
        for i, cat in enumerate(("Shopping", "Other", "Entertainment")):
            add_expense(logged_in.user_id, 100, cat, "2026-12-01", "Third %d" % i)
        html = html_of(logged_in, "?start=2026-12-01&end=2026-12-01")
        pcts = percents(html)
        assert len(pcts) == 3
        assert sum(pcts) == pytest.approx(100, abs=0.01)


class TestEmptyRange:
    def test_empty_range_shows_zero_state(self, logged_in):
        html = html_of(logged_in, "?start=2025-01-01&end=2025-01-31")
        assert "₹0.00" in stat_value(html, "Total spent")
        assert stat_value(html, "Transactions") == "0"
        assert stat_value(html, "Top category") == "—"
        assert "No transactions in this date range." in html
        assert row_count(html) == 0
        assert 'class="profile-bar-row"' not in html
        assert 'role="alert"' not in html


class TestInvalidInput:
    def test_start_after_end_shows_error_and_unfiltered_data(self, logged_in):
        html = html_of(logged_in, "?start=2026-11-05&end=2026-11-01")
        assert 'role="alert"' in html
        assert shown_descs(html) == ALL_DESCS
        assert "6,330.50" in stat_value(html, "Total spent")

    @pytest.mark.parametrize("param", ["start", "end"])
    def test_garbage_date_shows_error_and_ignores_bound(self, logged_in, param):
        html = html_of(logged_in, "?%s=garbage" % param)
        assert 'role="alert"' in html
        assert shown_descs(html) == ALL_DESCS

    @pytest.mark.parametrize(
        "value", ["2026-13-45", "2026-02-30", "11/05/2026", "2026-11-05T00:00"]
    )
    def test_malformed_or_impossible_dates_return_200_with_error(
        self, logged_in, value
    ):
        html = html_of(logged_in, "?start=" + value)
        assert 'role="alert"' in html
        assert shown_descs(html) == ALL_DESCS

    def test_valid_end_kept_when_start_garbage(self, logged_in):
        html = html_of(logged_in, "?start=garbage&end=2026-11-01")
        assert 'role="alert"' in html
        assert shown_descs(html) == ["Metro card", "Pharmacy"]

    @pytest.mark.parametrize(
        "payload",
        [
            "2026-01-01' OR '1'='1",
            "'; DROP TABLE expenses; --",
            "2026-11-01' UNION SELECT 1,2,3,4,5,6 --",
        ],
    )
    @pytest.mark.parametrize("param", ["start", "end"])
    def test_sql_injection_is_safe(self, logged_in, param, payload):
        response = logged_in.get("/profile", query_string={param: payload})
        assert response.status_code == 200
        html = response.data.decode()
        assert shown_descs(html) == ALL_DESCS
        assert "6,330.50" in stat_value(html, "Total spent")
        # Table still exists and data is intact afterwards.
        conn = db.get_db()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM expenses WHERE user_id = ?",
                (logged_in.user_id,),
            ).fetchone()[0]
        finally:
            conn.close()
        assert count == 4

    def test_non_padded_date_does_not_crash(self, logged_in):
        # Spec only requires "ignored with error" for malformed dates; either
        # outcome is acceptable here, but it must never be a 500.
        response = logged_in.get("/profile?start=2026-1-5")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "query", ["?start=&end=", "?start=", "?end=", "?start=%20%20&end="]
    )
    def test_blank_params_mean_no_bound_and_no_error(self, logged_in, query):
        html = html_of(logged_in, query)
        assert shown_descs(html) == ALL_DESCS
        assert 'role="alert"' not in html
        assert "Showing" not in html

    def test_blank_start_with_valid_end_acts_as_end_only(self, logged_in):
        html = html_of(logged_in, "?start=&end=2026-11-01")
        assert shown_descs(html) == ["Metro card", "Pharmacy"]
        assert 'role="alert"' not in html


class TestLimitAndIsolation:
    def test_limit_of_10_applies_within_range(self, logged_in, add_expense):
        for i in range(12):
            add_expense(
                logged_in.user_id, 10, "Food", "2026-12-%02d" % (i + 1), "Bulk %d" % i
            )
        html = html_of(logged_in, "?start=2026-12-01&end=2026-12-31")
        assert row_count(html) == 10
        assert stat_value(html, "Transactions") == "12"
        # Newest 10 shown: Dec 12 down to Dec 3.
        body = table_body(html)
        assert "Bulk 11" in body
        assert "Bulk 2" in body
        assert not re.search(r"Bulk 1(?!\d)", body)
        assert "Bulk 0" not in body
        assert "Electricity bill" not in body

    def test_other_users_expenses_never_included(
        self, logged_in, add_expense
    ):
        other_id = db.create_user("Other Person", "other@spendly.com", "secret123")
        add_expense(other_id, 99999, "Shopping", "2026-11-02", "OtherSecret")
        html = html_of(logged_in, "?start=2026-11-01&end=2026-11-05")
        assert "OtherSecret" not in html
        assert "99,999" not in html
        assert "5,550.50" in stat_value(html, "Total spent")
        assert stat_value(html, "Transactions") == "3"
        assert "profile-bar--shopping" not in html


PRESET_LABELS = ["This month", "3 months", "6 months"]


def preset_links(html):
    """Return {label: href} for the quick-range tabs."""
    found = re.findall(
        r'<a[^>]*class="profile-preset[^"]*"[^>]*href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>',
        html,
    )
    return {label: href.replace("&amp;", "&") for href, label in found}


class TestQuickRangeTabs:
    def test_three_tab_labels_render(self, logged_in):
        links = preset_links(html_of(logged_in))
        for label in PRESET_LABELS:
            assert label in links

    @pytest.mark.parametrize("label", PRESET_LABELS)
    def test_tab_links_to_profile_with_start_and_end(self, logged_in, label):
        href = preset_links(html_of(logged_in))[label]
        assert href.startswith("/profile?")
        assert re.search(r"[?&]start=\d{4}-\d{2}-\d{2}", href)
        assert re.search(r"[?&]end=\d{4}-\d{2}-\d{2}", href)

    @pytest.mark.parametrize("label", PRESET_LABELS)
    def test_tab_range_ends_today_and_start_not_after_end(self, logged_in, label):
        from datetime import date

        href = preset_links(html_of(logged_in))[label]
        end = re.search(r"end=(\d{4}-\d{2}-\d{2})", href).group(1)
        start = re.search(r"start=(\d{4}-\d{2}-\d{2})", href).group(1)
        assert end == date.today().isoformat()
        assert start <= end

    @pytest.mark.parametrize("label", PRESET_LABELS)
    def test_following_tab_link_returns_200_without_error(self, logged_in, label):
        href = preset_links(html_of(logged_in))[label]
        response = logged_in.get(href)
        assert response.status_code == 200
        assert 'role="alert"' not in response.data.decode()

    @pytest.mark.parametrize("label", PRESET_LABELS)
    def test_visited_tab_is_marked_active(self, logged_in, label):
        href = preset_links(html_of(logged_in))[label]
        html = logged_in.get(href).data.decode()
        assert "profile-preset--active" in html
        assert "aria-current" in html

    def test_no_tab_active_without_filter(self, logged_in):
        html = html_of(logged_in)
        assert "profile-preset--active" not in html
        assert "aria-current" not in html
