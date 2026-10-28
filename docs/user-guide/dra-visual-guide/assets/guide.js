/* Copyright 2026 The Volcano Authors. Licensed under the Apache License, Version 2.0. */
'use strict';
const menu = document.querySelector('.menu-toggle');
menu.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(open));
  document.getElementById('scene-nav').classList.toggle('open', open);
});
const data = document.getElementById('yaml-data');
if (data) {
  const docs = JSON.parse(data.textContent);
  const choices = [...document.querySelectorAll('.object-choice')];
  let selected = 0;
  const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  function highlight(yaml) {
    return yaml.split('\n').map(line => {
      if (line.trimStart().startsWith('#')) return '<span class="yaml-comment">' + escape(line) + '</span>';
      const parts = line.match(/^(\s*(?:- )?)([^:]+)(:)(.*)$/);
      if (!parts) return escape(line);
      return escape(parts[1]) + '<span class="yaml-key">' + escape(parts[2]) + '</span>:' + '<span class="yaml-string">' + escape(parts[4]) + '</span>';
    }).join('\n');
  }
  function select(index, updateHash = true) {
    selected = index;
    const doc = docs[index];
    choices.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
    document.getElementById('object-title').textContent = doc.kind + ' / ' + doc.name;
    document.getElementById('object-note').textContent = doc.note;
    document.getElementById('yaml-code').innerHTML = highlight(doc.yaml);
    document.getElementById('source-file').href = doc.file;
    document.getElementById('copy-status').textContent = '';
    if (updateHash) history.replaceState(null, '', '#object-' + index);
  }
  choices.forEach((button, index) => button.addEventListener('click', () => select(index)));
  const roles = {Node: 'node', ResourceSlice: 'slice', DeviceClass: 'cls', ResourceClaim: 'claim', Pod: 'pod'};
  document.querySelectorAll('.diagram [data-kind]').forEach(group => {
    let index = docs.findIndex(doc => roles[doc.kind] === group.dataset.kind && doc.name === group.dataset.name);
    if (index < 0) index = docs.findIndex(doc => roles[doc.kind] === group.dataset.kind);
    if (index < 0) return;
    group.setAttribute('tabindex', '0');
    group.setAttribute('role', 'button');
    group.setAttribute('aria-label', '查看 ' + docs[index].kind + ' YAML');
    const activate = () => {
      select(index);
      document.getElementById('resources').scrollIntoView({block: 'start'});
      choices[index].focus({preventScroll: true});
    };
    group.addEventListener('click', activate);
    group.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); }
    });
  });
  function restore() {
    const match = location.hash.match(/^#object-(\d+)$/);
    if (match && Number(match[1]) < docs.length) {
      select(Number(match[1]), false);
      document.getElementById('resources').scrollIntoView({block: 'start'});
    } else select(0, false);
  }
  restore();
  window.addEventListener('hashchange', restore);
  document.getElementById('copy-yaml').addEventListener('click', async () => {
    const status = document.getElementById('copy-status');
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(docs[selected].yaml);
      else {
        const area = document.createElement('textarea');
        area.value = docs[selected].yaml;area.style.position = 'fixed';area.style.opacity = '0';
        document.body.append(area);area.select();
        const copied = document.execCommand('copy');area.remove();
        if (!copied) throw new Error('clipboard unavailable');
      }
      status.textContent = '已复制';
    } catch (_) { status.textContent = '请选中代码后复制'; }
  });
}
const cores = document.getElementById('cores');
if (cores) {
  const memory = document.getElementById('memory');
  function updateCapacity() {
    const c = Number(cores.value), m = Number(memory.value);
    document.getElementById('cores-value').textContent = c;
    document.getElementById('memory-value').textContent = m + 'Gi';
    const result = document.getElementById('capacity-result');
    const fits = c <= 40 && m <= 16;
    result.classList.toggle('fail', !fits);
    result.textContent = fits ? `可以分配。分配后剩余 ${40-c} 算力、${16-m}Gi 显存。` : `这张卡放不下：${[c > 40 ? '算力还差 ' + (c-40) : '', m > 16 ? '显存还差 ' + (m-16) + 'Gi' : ''].filter(Boolean).join('，')}。`;
  }
  cores.addEventListener('input', updateCapacity);
  memory.addEventListener('input', updateCapacity);
  updateCapacity();
}
