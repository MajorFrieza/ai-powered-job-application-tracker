(() => {
    const selects = document.querySelectorAll('[data-status-url]');
    const token = document.cookie
        .split('; ')
        .find((cookie) => cookie.startsWith('csrftoken='))
        ?.slice('csrftoken='.length);
    const csrfToken = token ? decodeURIComponent(token) : '';

    for (const select of selects) {
        select.addEventListener('change', async () => {
            const previousStatus = select.dataset.status;
            select.disabled = true;
            try {
                const response = await fetch(select.dataset.statusUrl, {
                    method: 'PATCH',
                    headers: {
                        Accept: 'application/json',
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    body: JSON.stringify({ status: select.value }),
                });
                const result = await response.json();
                if (!response.ok) {
                    throw new Error(result.detail || `Could not update status (HTTP ${response.status}).`);
                }

                const row = select.closest('[data-application-row]');
                row.dataset.status = result.status;
                select.dataset.status = result.status;
                updateSummary(previousStatus, result.status);
                const search = document.querySelector('[data-application-search]');
                const statusFilter = document.querySelector('[data-status-filter]');
                if (statusFilter?.value && statusFilter.value !== result.status) row.hidden = true;
                if (search?.value && !(row.dataset.search || '').includes(search.value.trim().toLowerCase())) row.hidden = true;
            } catch (error) {
                select.value = previousStatus;
                window.alert(error.message);
            } finally {
                select.disabled = false;
            }
        });
    }

    const updateSummary = (oldStatus, newStatus) => {
        if (oldStatus === newStatus) return;
        for (const [status, delta] of [[oldStatus, -1], [newStatus, 1]]) {
            const count = document.querySelector(
                `[data-summary-status="${CSS.escape(status)}"] [data-summary-count]`,
            );
            if (count) count.textContent = String(Math.max(0, Number(count.textContent) + delta)).padStart(2, '0');
        }
    };
})();
