'use strict';

const samplePanel = document.querySelector('[data-sensitivity]');
if (samplePanel) {
  const toggle = samplePanel.querySelector('[data-sample-toggle]');
  const samples = {
    all: {steps: '6,889.7', active: '209.8', days: '988', label: 'All full-coverage days. Each daily record has equal weight.'},
    positive: {steps: '8,321.5', active: '253.2', days: '818', label: 'Positive-step full-coverage days. Each daily record has equal weight.'}
  };
  const renderSample = () => {
    const sample = toggle.checked ? samples.all : samples.positive;
    samplePanel.querySelector('[data-mean-steps]').textContent = sample.steps;
    samplePanel.querySelector('[data-active-minutes]').textContent = sample.active;
    samplePanel.querySelector('[data-day-count]').textContent = sample.days;
    samplePanel.querySelector('[data-sample-status]').textContent = sample.label;
  };
  toggle.disabled = false;
  toggle.addEventListener('change', renderSample);
  renderSample();
}

const user = document.documentElement.dataset.githubUsername || '';
const repository = document.documentElement.dataset.githubRepository || '';
if (/^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/.test(user)) {
  for (const link of document.querySelectorAll('[data-github-profile]')) {
    link.href = `https://github.com/${encodeURIComponent(user)}`;
    link.hidden = false;
  }
  if (repository && /^[a-zA-Z0-9_.-]+$/.test(repository)) {
    for (const link of document.querySelectorAll('[data-github-repo]')) {
      link.href = `https://github.com/${encodeURIComponent(user)}/${encodeURIComponent(repository)}`;
      link.hidden = false;
    }
  }
}
