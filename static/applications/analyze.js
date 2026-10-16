(() => {
    const form = document.querySelector('#analysis-form');
    const description = document.querySelector('#id_job_description');
    const resultContainer = document.querySelector('#analysis-result');
    const errorContainer = document.querySelector('#analysis-error');
    if (!form || !description || !resultContainer || !errorContainer) return;

    const csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
    const button = form.querySelector('button[type=submit]');

    const addText = (parent, tagName, className, text) => {
        const element = document.createElement(tagName);
        if (className) element.className = className;
        element.textContent = text;
        parent.append(element);
        return element;
    };

    const renderAnalysis = (analysis) => {
        resultContainer.replaceChildren();
        const card = document.createElement('div');
        card.className = 'card bg-light';
        const body = document.createElement('div');
        body.className = 'card-body';
        addText(body, 'h3', 'h6', 'Summary');
        addText(body, 'p', '', analysis.summary);

        for (const [heading, skills] of [
            ['Required skills', analysis.required_skills],
            ['Skills to highlight', analysis.skills_to_highlight],
        ]) {
            addText(body, 'h3', 'h6', heading);
            const list = document.createElement('ul');
            for (const skill of skills) addText(list, 'li', '', skill);
            body.append(list);
        }
        card.append(body);
        resultContainer.append(card);
    };

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        errorContainer.textContent = '';
        if (!description.value.trim()) {
            errorContainer.textContent = 'Paste a job description in the field above first.';
            description.focus();
            return;
        }

        button.disabled = true;
        button.textContent = 'Analyzing…';
        try {
            const response = await fetch(form.dataset.endpoint, {
                method: 'POST',
                headers: {
                    Accept: 'application/json',
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfInput.value,
                },
                body: JSON.stringify({ job_description: description.value }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || Object.values(data).flat().join(' ') || `Analysis failed (HTTP ${response.status}).`);
            }
            renderAnalysis(data.ai_analysis);
        } catch (error) {
            errorContainer.textContent = error.message;
        } finally {
            button.disabled = false;
            button.textContent = 'Analyze with AI';
        }
    });
})();
