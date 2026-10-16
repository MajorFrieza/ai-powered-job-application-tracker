(() => {
    const board = document.querySelector('#application-board');
    const message = document.querySelector('#board-message');
    if (!board || !message) return;

    const columns = Array.from(board.querySelectorAll('.board-column'));
    const searchInput = document.querySelector('[data-application-search]');
    const statusFilter = document.querySelector('[data-status-filter]');

    const getCsrfToken = () => {
        const cookie = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='));
        return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
    };

    const showMessage = (text) => {
        message.className = 'alert alert-danger';
        message.textContent = text;
    };

    const updateCounts = () => {
        for (const column of columns) {
            const count = column.querySelectorAll('.application-card').length;
            column.querySelector('[data-count]').textContent = count;
            const summary = document.querySelector(
                `[data-summary-status="${CSS.escape(column.dataset.status)}"] [data-summary-count]`,
            );
            if (summary) summary.textContent = String(count).padStart(2, '0');
        }
    };

    const applyFilters = () => {
        const query = searchInput?.value.trim().toLowerCase() || '';
        const selectedStatus = statusFilter?.value || '';
        for (const card of board.querySelectorAll('.application-card')) {
            card.hidden = !(card.dataset.search.includes(query)
                && (!selectedStatus || card.dataset.status === selectedStatus));
        }
    };

    const createCard = (application) => {
        const card = document.createElement('article');
        card.className = 'card application-card';
        card.draggable = true;
        card.dataset.applicationId = application.id;
        card.dataset.status = application.status;
        card.dataset.search = `${application.company} ${application.role} ${application.notes || ''}`.toLowerCase();

        const body = document.createElement('div');
        body.className = 'card-body';
        const companyRow = document.createElement('div');
        companyRow.className = 'card-company-row';
        const mark = document.createElement('span');
        mark.className = 'company-mark';
        mark.setAttribute('aria-hidden', 'true');
        mark.textContent = application.company.slice(0, 1).toUpperCase();
        const company = document.createElement('span');
        company.className = 'company-name';
        company.textContent = application.company;

        const dropdown = document.createElement('div');
        dropdown.className = 'dropdown ms-auto';
        const menuButton = document.createElement('button');
        menuButton.className = 'card-menu';
        menuButton.type = 'button';
        menuButton.dataset.bsToggle = 'dropdown';
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.setAttribute('aria-label', `Actions for ${application.company}`);
        menuButton.textContent = '···';
        const menu = document.createElement('ul');
        menu.className = 'dropdown-menu dropdown-menu-end';
        const editItem = document.createElement('li');
        const editLink = document.createElement('a');
        editLink.className = 'dropdown-item';
        editLink.href = `/applications/${encodeURIComponent(application.id)}/edit/`;
        editLink.textContent = 'Edit';
        editItem.append(editLink);
        const deleteItem = document.createElement('li');
        const deleteForm = document.createElement('form');
        deleteForm.method = 'post';
        deleteForm.action = `/applications/${encodeURIComponent(application.id)}/delete/`;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = getCsrfToken();
        const deleteButton = document.createElement('button');
        deleteButton.className = 'dropdown-item text-danger';
        deleteButton.type = 'submit';
        deleteButton.textContent = 'Delete';
        deleteForm.append(csrfInput, deleteButton);
        deleteForm.addEventListener('submit', (event) => {
            if (!window.confirm('Delete this application?')) event.preventDefault();
        });
        deleteItem.append(deleteForm);
        menu.append(editItem, deleteItem);
        dropdown.append(menuButton, menu);
        companyRow.append(mark, company, dropdown);

        const role = document.createElement('p');
        role.className = 'application-role';
        role.textContent = application.role;
        const tags = document.createElement('div');
        tags.className = 'application-meta';
        const dateTag = document.createElement('span');
        dateTag.className = 'application-tag';
        dateTag.textContent = `Applied ${application.date_applied}`;
        tags.append(dateTag);
        body.append(companyRow, role, tags);

        const footer = document.createElement('div');
        footer.className = 'application-card-footer';
        const date = document.createElement('span');
        date.textContent = application.date_applied;
        footer.append(date);
        if (application.job_link) {
            const link = document.createElement('a');
            link.href = application.job_link;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = '↗';
            link.setAttribute('aria-label', 'View job posting');
            footer.append(link);
        }
        body.append(footer);
        card.append(body);
        card.addEventListener('dragstart', (event) => {
            card.classList.add('is-dragging');
            event.dataTransfer.setData('text/plain', application.id);
            event.dataTransfer.effectAllowed = 'move';
        });
        card.addEventListener('dragend', () => card.classList.remove('is-dragging'));
        return card;
    };

    const loadApplications = async () => {
        try {
            const response = await fetch('/api/applications/?format=json', {
                headers: { Accept: 'application/json' },
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || `Could not load applications (HTTP ${response.status}).`);
            }
            for (const column of columns) column.querySelector('[data-cards]').replaceChildren();
            for (const application of result) {
                const column = columns.find((item) => item.dataset.status === application.status);
                if (column) column.querySelector('[data-cards]').append(createCard(application));
            }
            for (const column of columns) {
                if (!column.querySelector('.application-card')) {
                    const empty = document.createElement('p');
                    empty.className = 'text-secondary small text-center py-3 mb-0';
                    empty.textContent = 'No applications';
                    column.querySelector('[data-cards]').append(empty);
                }
            }
            updateCounts();
            applyFilters();
            message.className = 'alert d-none';
        } catch (error) {
            showMessage(`${error.message} Check your MongoDB connection and try again.`);
        }
    };

    for (const column of columns) {
        column.addEventListener('dragover', (event) => {
            event.preventDefault();
            column.classList.add('is-drop-target');
        });
        column.addEventListener('dragleave', (event) => {
            if (!column.contains(event.relatedTarget)) column.classList.remove('is-drop-target');
        });
        column.addEventListener('drop', async (event) => {
            event.preventDefault();
            column.classList.remove('is-drop-target');
            const applicationId = event.dataTransfer.getData('text/plain');
            const card = board.querySelector(`[data-application-id="${CSS.escape(applicationId)}"]`);
            if (!card || card.closest('.board-column') === column) return;
            const previousCards = card.parentElement;
            try {
                const response = await fetch(`/api/applications/${encodeURIComponent(applicationId)}/status/`, {
                    method: 'PATCH',
                    headers: {
                        Accept: 'application/json',
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                    },
                    body: JSON.stringify({ status: column.dataset.status }),
                });
                const result = await response.json();
                if (!response.ok) {
                    throw new Error(result.detail || `Could not move application (HTTP ${response.status}).`);
                }

                column.querySelector('[data-cards] > p')?.remove();
                column.querySelector('[data-cards]').append(card);
                card.dataset.status = result.status;
                if (!previousCards.querySelector('.application-card')) {
                    const empty = document.createElement('p');
                    empty.className = 'text-secondary small text-center py-3 mb-0';
                    empty.textContent = 'No applications';
                    previousCards.append(empty);
                }
                updateCounts();
                applyFilters();
                message.className = 'alert d-none';
            } catch (error) {
                showMessage(`${error.message} The card was left in its previous column.`);
            }
        });
    }

    searchInput?.addEventListener('input', applyFilters);
    statusFilter?.addEventListener('change', applyFilters);
    board.addEventListener('click', (event) => {
        const button = event.target.closest('[data-add-status]');
        if (!button) return;
        const statusSelect = document.querySelector('#id_status');
        if (statusSelect) statusSelect.value = button.dataset.addStatus;
    });

    loadApplications();
})();
