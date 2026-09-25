(() => {
  const $ = (id) => document.getElementById(id);
  const TAC_SIZE = 520;
  let ws = null;
  let token = '';
  let channels = [];
  let ships = [];
  let state = null;
  let dragId = null;
  let players = [];

  const status = (t, ok = false) => {
    $('status').textContent = t;
    $('status').className = `status ${ok ? 'live' : t === 'offline' ? '' : 'bad'}`;
  };
  const send = (m) => ws && ws.readyState === WebSocket.OPEN && ws.send(JSON.stringify(m));
  const error = (m) => {
    $('error').textContent = m;
    status('error');
  };
  const currentRoom = () => $('room').value;

  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  const shipOptions = (selected) =>
    ['<option value="">— catalog default —</option>']
      .concat(
        ships.map(
          (s) =>
            `<option value="${esc(s.id)}" ${s.id === selected ? 'selected' : ''}>${esc(s.name)} · ${esc(s.role)} · m${s.massKt} p${s.profile} s${s.stealth}</option>`,
        ),
      )
      .join('');

  const roomOptions = () => {
    $('room').innerHTML = channels.length
      ? channels
          .map((c) => `<option value="${esc(c.channelId)}">${esc(c.title)} · ${c.status} · ${c.players} crew</option>`)
          .join('')
      : '<option value="">No active rooms</option>';
  };

  const renderPlayers = () => {
    $('players').innerHTML = players.length
      ? players.map((p) => `<div class="contact"><span><strong>${esc(p.name || 'Unnamed')}</strong><small>${esc(p.userId)} · ${esc(p.channelId)} · ${esc(p.seat || 'unseated')}</small></span><button data-kick="${esc(p.sessionId)}" data-kick-room="${esc(p.channelId)}">BOOT</button></div>`).join('')
      : '<span class="empty">No players connected.</span>';
    document.querySelectorAll('[data-kick]').forEach((button) => {
      button.onclick = () => {
        if (confirm(`Remove ${button.parentElement.querySelector('strong').textContent}?`))
          send({ type: 'admin.kick', channelId: button.dataset.kickRoom, sessionId: button.dataset.kick });
      };
    });
  };

  const campaignOptions = (list) => {
    $('campaign').innerHTML =
      '<option value="">Default</option>' +
      list.map((c) => `<option value="${esc(c.id)}">${esc(c.title)} · ${esc(c.theater)}</option>`).join('');
  };

  const fillSpawnType = () => {
    const types = ['escort', 'fighter', 'capship', 'carrier', 'freighter', 'liner', 'prospector', 'asteroid', 'nebula', 'debris', 'dust', 'ice'];
    $('spawn-type').innerHTML = types.map((t) => `<option value="${t}">${t}</option>`).join('');
  };

  // ---- tactical map -------------------------------------------------------

  const mapScale = (radius) => (TAC_SIZE - 60) / (radius * 2.8 || 1);

  function worldToSvg(p, center, radius) {
    const scale = mapScale(radius);
    return {
      x: TAC_SIZE / 2 + (p.x - center.x) * scale,
      y: TAC_SIZE / 2 - (p.y - center.y) * scale,
      scale,
    };
  }

  function svgToWorld(sx, sy, center, radius) {
    const scale = mapScale(radius);
    return {
      x: Math.round(center.x + (sx - TAC_SIZE / 2) / scale),
      y: Math.round(center.y - (sy - TAC_SIZE / 2) / scale),
    };
  }

  function svgPoint(svg, e) {
    const rect = svg.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * TAC_SIZE,
      y: ((e.clientY - rect.top) / rect.height) * TAC_SIZE,
    };
  }

  function renderMap(s) {
    if (dragId) return; // don't rebuild mid-drag
    const svg = $('tac-map');
    const center = s.campaign.patrol.center;
    const radius = s.campaign.patrol.radiusKlik;
    const parts = [];
    const ringR = radius * mapScale(radius);
    parts.push(`<circle cx="${TAC_SIZE / 2}" cy="${TAC_SIZE / 2}" r="${ringR.toFixed(1)}" fill="none" stroke="#1d3a4a" stroke-dasharray="4 5"/>`);
    parts.push(`<line x1="0" y1="${TAC_SIZE / 2}" x2="${TAC_SIZE}" y2="${TAC_SIZE / 2}" stroke="#12242f"/>`);
    parts.push(`<line x1="${TAC_SIZE / 2}" y1="0" x2="${TAC_SIZE / 2}" y2="${TAC_SIZE}" stroke="#12242f"/>`);

    const colors = { ice: '#5aa9d6', dust: '#b08a5a', nebula: '#8a6ad0', debris: '#8899aa', asteroid: '#9a7a4a' };

    for (const ct of s.contacts) {
      if (!ct.radiusKlik) continue;
      const p = worldToSvg(ct.pos, center, radius);
      const r = Math.max(5, ct.radiusKlik * p.scale);
      const col = colors[ct.trueType] || '#7a6a4a';
      parts.push(`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${r.toFixed(1)}" fill="${col}22" stroke="${col}" stroke-dasharray="3 3"/>`);
      parts.push(`<text x="${p.x.toFixed(1)}" y="${(p.y - r - 4).toFixed(1)}" fill="${col}" font-size="10" text-anchor="middle">${esc(ct.trueType)}</text>`);
    }

    for (const ct of s.contacts) {
      if (ct.radiusKlik) continue;
      const p = worldToSvg(ct.pos, center, radius);
      const col = ct.hostile ? '#ff6b73' : ct.faction === 'friendly' ? '#64ed9c' : '#42d9e7';
      parts.push(
        `<g class="tac-contact" data-id="${esc(ct.id)}" style="cursor:grab">` +
          `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="8" fill="${col}33" stroke="${col}"/>` +
          `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3.2" fill="${col}"/>` +
          `<text x="${(p.x + 12).toFixed(1)}" y="${(p.y + 3).toFixed(1)}" fill="${col}" font-size="10">${esc(ct.name)}</text>` +
          `</g>`,
      );
    }

    const sp = worldToSvg(s.ship.pos, center, radius);
    parts.push(`<polygon points="${sp.x},${sp.y - 9} ${sp.x + 6},${sp.y + 7} ${sp.x - 6},${sp.y + 7}" fill="#42d9e7"/>`);
    parts.push(`<text x="${(sp.x + 10).toFixed(1)}" y="${(sp.y + 3).toFixed(1)}" fill="#42d9e7" font-size="10">${esc(s.ship.name)}</text>`);

    svg.innerHTML = parts.join('');
    attachDrag(s);
  }

  function attachDrag(s) {
    const svg = $('tac-map');
    const center = s.campaign.patrol.center;
    const radius = s.campaign.patrol.radiusKlik;
    svg.querySelectorAll('.tac-contact').forEach((el) => {
      const first = el.querySelector('circle');
      const ox = Number(first.getAttribute('cx'));
      const oy = Number(first.getAttribute('cy'));
      let world = null;
      const onMove = (e) => {
        const pt = svgPoint(svg, e);
        world = svgToWorld(pt.x, pt.y, center, radius);
        el.setAttribute('transform', `translate(${(pt.x - ox).toFixed(1)},${(pt.y - oy).toFixed(1)})`);
      };
      const onUp = () => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
        dragId = null;
        if (world) {
          send({
            type: 'admin.update',
            channelId: currentRoom(),
            contactId: el.dataset.id,
            patch: { pos: { x: world.x, y: world.y, z: 0 } },
          });
        } else {
          renderMap(state);
        }
      };
      el.addEventListener('pointerdown', (ev) => {
        ev.preventDefault();
        dragId = el.dataset.id;
        world = null;
        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
      });
    });
  }

  // ---- state --------------------------------------------------------------

  const renderState = (s) => {
    state = s;
    const frozen = !!s.timeFrozen;
    $('room-meta').textContent = `${s.status.toUpperCase()} · ${s.clock.toFixed(1)} MIN · tension ${Math.round(s.war.tension)}%${frozen ? ' · TIME FROZEN' : ''}`;
    $('freeze').textContent = frozen ? 'RESUME TIME' : 'FREEZE TIME';
    $('freeze').classList.toggle('frozen', frozen);
    $('map-hint').textContent = frozen
      ? 'TIME FROZEN — drag a contact to reposition it.'
      : 'Drag a contact to move it. Freeze time first.';

    $('state').innerHTML = `
      <div class="contact">
        <span><strong>${esc(s.campaign.title)}</strong><small>${esc(s.campaign.theater)}</small></span>
        <span>${s.contacts.length} contacts</span>
      </div>
      <div class="ownship">
        <span class="eyebrow">CREW SHIP</span>
        <strong>${esc(s.ship.name)}</strong>
        <small>${esc(s.ship.class)} · ${esc(s.ship.shipClass || '—')}</small>
        <div class="chips">
          <span class="chip">SPD ${Math.round(s.ship.speed)}/${Math.round(s.ship.maxSpeed)} kps</span>
          <span class="chip">MASS ${s.ship.massKt} kt</span>
          <span class="chip">PROFILE ${Math.round((s.ship.profile || 0) * 100)}%</span>
          <span class="chip">STEALTH ${Math.round((s.ship.stealth || 0) * 100)}%</span>
          <span class="chip">EMISSION ${Math.round((s.ship.emission || 0) * 100)}%</span>
        </div>
      </div>`;

    if (s.ship.shipClass) $('crew-ship').value = s.ship.shipClass;

    $('skills').innerHTML =
      Object.values(s.seats || {})
        .map((seat) => {
          const scores = (seat.skills && seat.skills.scores) || {};
          const entries = Object.entries(scores);
          const line = entries.length
            ? entries.map(([k, v]) => `${esc(k)} ${v}`).join(' · ')
            : 'crew average';
          return `<div class="contact"><span><strong>${esc(seat.title)}</strong><small>${line}</small></span></div>`;
        })
        .join('') || '<span class="empty">No seats.</span>';

    $('contacts').innerHTML = s.contacts.length
      ? s.contacts
          .map(
            (c) => `
        <div class="contact contact-edit">
          <img class="ship-thumb" src="${esc(c.image || c.vdu || '/img/brief/unknown.png')}" alt="${esc(c.trueType)}" />
          <span>
            <strong>${esc(c.name)}</strong>
            <small>${esc(c.id)} · ${esc(c.trueType)} · ${esc(c.faction)}${c.hostile ? ' · HOSTILE' : ''}${
              c.gravSaturated ? ' · GRAV SATURATED' : ''
            }</small>
            <select data-contact="${esc(c.id)}" class="ship-pick">${shipOptions(c.shipClass)}</select>
          </span>
          <span class="contact-actions">
            <button data-remove="${esc(c.id)}">REMOVE</button>
          </span>
        </div>`,
          )
          .join('')
      : '<span class="empty">No contacts.</span>';

    document.querySelectorAll('.ship-pick').forEach((sel) => {
      sel.onchange = (e) =>
        send({ type: 'admin.update', channelId: currentRoom(), contactId: e.target.dataset.contact, patch: { shipClass: e.target.value } });
    });
    document.querySelectorAll('[data-remove]').forEach((btn) => {
      btn.onclick = (e) => send({ type: 'admin.remove', channelId: currentRoom(), contactId: e.target.dataset.remove });
    });

    renderMap(s);
  };

  function connect() {
    token = $('token').value;
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/`);
    status('connecting');
    ws.onopen = () => send({ type: 'admin.hello', token });
    ws.onclose = () => status('offline');
    ws.onmessage = ({ data }) => {
      const m = JSON.parse(data);
      if (m.type === 'admin.error') return error(m.message);
      if (m.type === 'admin.ok') {
        channels = m.channels;
        ships = m.ships || [];
        players = m.players || [];
        roomOptions();
        renderPlayers();
        campaignOptions(m.campaigns);
        $('crew-ship').innerHTML = shipOptions('');
        $('spawn-ship').innerHTML = shipOptions('');
        if ((m.skills || []).length && !$('skill-name').options.length) {
          $('skill-name').innerHTML = m.skills
            .map((n) => `<option value="${esc(n)}">${esc(n)}</option>`)
            .join('');
        }
        $('login').hidden = true;
        $('console').hidden = false;
        status('connected', true);
      }
      if (m.type === 'admin.state') renderState(m.state);
    };
  }

  $('login-form').onsubmit = (e) => {
    e.preventDefault();
    connect();
  };
  $('refresh').onclick = () => send({ type: 'admin.list' });
  $('skill-btn').onclick = () => {
    const channelId = currentRoom();
    const skill = $('skill-name').value;
    if (!channelId || !skill) return error('Select a room and a skill first.');
    send({
      type: 'admin.skills',
      channelId,
      seat: $('skill-seat').value,
      scores: { [skill]: Number($('skill-score').value) },
    });
  };
  $('subscribe').onclick = () => {
    if (currentRoom()) send({ type: 'admin.subscribe', channelId: currentRoom() });
  };
  $('new-engagement').onclick = () => {
    const channelId = currentRoom();
    if (!channelId) return error('Select a room before starting an engagement.');
    if (confirm('Reset this room and start a new engagement?'))
      send({
        type: 'admin.reset',
        channelId,
        campaignId: $('campaign').value || null,
        shipId: $('crew-ship').value || null,
      });
  };
  $('set-ship').onclick = () => {
    const channelId = currentRoom();
    if (!channelId) return error('Select a room first.');
    send({ type: 'admin.setShip', channelId, shipId: $('crew-ship').value });
  };
  $('freeze').onclick = () => {
    const channelId = currentRoom();
    if (!channelId) return error('Select a room first.');
    send({ type: 'admin.freeze', channelId, frozen: !(state && state.timeFrozen) });
  };
  $('spawn-btn').onclick = () => {
    const channelId = currentRoom();
    if (!channelId) return error('Select a room first.');
    send({
      type: 'admin.spawn',
      channelId,
      contact: {
        type: $('spawn-type').value,
        shipClass: $('spawn-ship').value || null,
        x: Number($('spawn-x').value) || 0,
        y: Number($('spawn-y').value) || 0,
        heading: 0,
        speed: 60,
        faction: $('spawn-hostile').checked ? 'enemy' : 'neutral',
        hostile: $('spawn-hostile').checked,
        emitting: $('spawn-hostile').checked,
      },
    });
  };
  $('room').onchange = () => send({ type: 'admin.list' });
  fillSpawnType();
})();
