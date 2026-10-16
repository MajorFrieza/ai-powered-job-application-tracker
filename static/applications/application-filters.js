(() => {
    const search = document.querySelector('[data-application-search]');
    const statusFilter = document.querySelector('[data-status-filter]');
    if (!search && !statusFilter) return;

    const rows = Array.from(document.querySelectorAll('[data-application-row]'));
    const cards = Array.from(document.querySelectorAll('.application-card'));
    const emptyMessage = document.querySelector('[data-filter-empty]');

    const update = () => {
        const query = search?.value.trim().toLowerCase() || '';
        const status = statusFilter?.value || '';
        let visibleRows = 0;

        for (const element of [...rows, ...cards]) {
            const matchesText = (element.dataset.search || '').includes(query);
            const matchesStatus = !status || element.dataset.status === status;
            element.hidden = !matchesText || !matchesStatus;
            if (rows.includes(element) && !element.hidden) visibleRows += 1;
        }

        if (emptyMessage) emptyMessage.classList.toggle('d-none', visibleRows > 0);
    };

    search?.addEventListener('input', update);
    statusFilter?.addEventListener('change', update);
})();
