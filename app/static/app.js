// Initialize lucide icons
lucide.createIcons();

const API_BASE = window.location.origin;

// State
let currentState = {
  task: 'medium',
  alarms: [],
  networkSummary: null,
  stepsTaken: 0,
  maxSteps: 30,
  falsePositives: 0,
  reward: 0,
  done: false
};
let selectedNodeId = null;
let graphData = { nodes: [], links: [] };
let simulation;

// DOM Elements
const els = {
  btnReset: document.getElementById('btnReset'),
  taskSelect: document.getElementById('taskSelect'),
  statusText: document.getElementById('statusText'),
  statusBadge: document.getElementById('statusBadge'),
  timeElapsed: document.getElementById('timeElapsed'),
  graphContainer: document.getElementById('graphContainer'),
  alarmsList: document.getElementById('alarmsList'),
  alarmCount: document.getElementById('alarmCount'),
  currentTarget: document.getElementById('currentTarget'),
  consoleOutput: document.getElementById('consoleOutput'),
  valSteps: document.getElementById('valSteps'),
  pbSteps: document.getElementById('pbSteps'),
  valFP: document.getElementById('valFP'),
  valReward: document.getElementById('valReward'),
  endModal: document.getElementById('endModal'),
  filterBtns: document.querySelectorAll('.filter-btn')
};

// Console Log Helper
function log(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `console-line ${type}`;
  const time = new Date().toLocaleTimeString('en-US', { hour12: false });
  el.innerHTML = `<span style="color:#64748b">[${time}]</span> ${msg}`;
  els.consoleOutput.appendChild(el);
  els.consoleOutput.scrollTop = els.consoleOutput.scrollHeight;
}

// Timer
let startTime;
let timerInterval;
function startTimer() {
  clearInterval(timerInterval);
  startTime = Date.now();
  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    els.timeElapsed.innerText = `${m}:${s}`;
  }, 1000);
}

// Actions
async function apiPost(endpoint, body) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    log(`Network error: ${err.message}`, 'error');
    throw err;
  }
}

els.btnReset.addEventListener('click', async () => {
  const task = els.taskSelect.value;
  els.btnReset.disabled = true;
  els.btnReset.innerHTML = `<i data-lucide="loader" class="spin"></i> Initializing...`;
  lucide.createIcons();
  
  try {
    log(`Resetting environment for task: ${task}`, 'info');
    const obs = await apiPost('/reset', { task, seed: Date.now() });
    
    currentState = {
      task,
      alarms: obs.active_alarms,
      networkSummary: obs.network_summary,
      stepsTaken: 0,
      maxSteps: obs.steps_remaining, // Use as initial
      falsePositives: 0,
      reward: 0,
      done: false
    };
    buildGraphData(obs.network_summary, obs.active_alarms);
    updateUI();
    startTimer();
    els.endModal.classList.add('hidden');
    log('Environment ready. Initial state loaded.', 'info');
  } catch(e) {
    log('Failed to reset environment.', 'error');
  } finally {
    els.btnReset.disabled = false;
    els.btnReset.innerHTML = `<i data-lucide="power"></i> Initialize Task`;
    lucide.createIcons();
  }
});

function buildGraphData(network, alarms) {
  const alarmMap = {};
  alarms.forEach(a => alarmMap[a.node_id] = a.severity);
  
  const nodes = [];
  const links = [];
  
  // Create nodes from layers
  ['power_units', 'core_switches', 'radio_controllers', 'cell_towers'].forEach(layer => {
    (network[layer] || []).forEach(n => {
      nodes.push({
        id: n.id,
        layer,
        status: alarmMap[n.id] ? alarmMap[n.id] : 'UP'
      });
      // Infer links based on IDs
      if (layer === 'core_switches') links.push({ source: n.id, target: `PWR_${n.id.split('_')[1]}`});
      if (layer === 'radio_controllers') links.push({ source: n.id, target: `SW_${n.id.split('_')[1]}_${n.id.split('_')[2]}`});
      if (layer === 'cell_towers') links.push({ source: n.id, target: `RC_${n.id.split('_')[1]}_${n.id.split('_')[2]}_${n.id.split('_')[3]}`});
    });
  });
  
  graphData = { nodes, links };
  renderD3Graph();
}

function renderD3Graph() {
  els.graphContainer.innerHTML = '';
  const width = els.graphContainer.clientWidth;
  const height = els.graphContainer.clientHeight;
  
  const svg = d3.select('#graphContainer').append('svg')
    .attr('width', width)
    .attr('height', height);
    
  const g = svg.append('g');

  const zoom = d3.zoom().on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoom);
  
  simulation = d3.forceSimulation(graphData.nodes)
    .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(40))
    .force('charge', d3.forceManyBody().strength(-80))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const link = g.append('g')
    .selectAll('line')
    .data(graphData.links)
    .enter().append('line')
    .attr('class', 'link');

  const node = g.append('g')
    .selectAll('g')
    .data(graphData.nodes)
    .enter().append('g')
    .attr('class', 'node')
    .on('click', (e, d) => {
      document.querySelectorAll('.node').forEach(n => n.classList.remove('selected'));
      e.currentTarget.classList.add('selected');
      selectedNodeId = d.id;
      els.currentTarget.innerText = d.id;
    })
    .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

  node.append('circle')
    .attr('r', 8)
    .attr('fill', d => {
      if (d.status === 'CRITICAL') return 'var(--status-failed)';
      if (d.status === 'MAJOR' || d.status === 'WARNING') return 'var(--status-degraded)';
      return 'var(--status-up)';
    });

  // Optional labels for higher scale if desired, but hidden by default in CSS until zoom

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    node
      .attr('transform', d => `translate(${d.x},${d.y})`);
  });

  function dragstarted(e) {
    if (!e.active) simulation.alphaTarget(0.3).restart();
    e.subject.fx = e.subject.x;
    e.subject.fy = e.subject.y;
  }
  function dragged(e) {
    e.subject.fx = e.x;
    e.subject.fy = e.y;
  }
  function dragended(e) {
    if (!e.active) simulation.alphaTarget(0);
    e.subject.fx = null;
    e.subject.fy = null;
  }
}

function updateUI() {
  // Update alarms
  els.alarmsList.innerHTML = '';
  els.alarmCount.innerText = currentState.alarms.length;
  
  if (currentState.alarms.length === 0) {
    els.alarmsList.innerHTML = '<div class="empty-state">No active alarms</div>';
  } else {
    currentState.alarms.forEach(a => {
      const card = document.createElement('div');
      card.className = `alarm-card ${a.severity}`;
      card.innerHTML = `
        <div class="alarm-id"><span>${a.node_id}</span> <span style="font-size:0.7em">${a.severity}</span></div>
        <div class="alarm-msg">${a.message}</div>
      `;
      card.onclick = () => {
        selectedNodeId = a.node_id;
        els.currentTarget.innerText = a.node_id;
      };
      els.alarmsList.appendChild(card);
    });
  }

  // Update metrics
  els.valSteps.innerText = `${currentState.stepsTaken} / ${currentState.maxSteps}`;
  els.pbSteps.style.width = `${Math.min(100, (currentState.stepsTaken / currentState.maxSteps) * 100)}%`;
  els.valFP.innerText = currentState.falsePositives;
  els.valReward.innerText = currentState.reward.toFixed(4);
}

// Handle action
window.selectAction = async function(actionType) {
  if (currentState.done) return log('Episode is done. Please initialize a new task.', 'error');
  if (!selectedNodeId) return log('Error: No target node selected.', 'error');
  
  log(`> Executing ${actionType} on ${selectedNodeId}...`, 'action');
  
  try {
    const res = await apiPost('/step', {
      task: currentState.task,
      action: {
        action_type: actionType,
        target_node_id: selectedNodeId
      }
    });

    currentState.stepsTaken++;
    currentState.alarms = res.observation.active_alarms;
    currentState.reward += res.reward;
    currentState.done = res.done;
    
    // Check info for FP
    if (res.info.status === 'FALSE_POSITIVE' || res.info.result === 'FALSE_POSITIVE') {
      currentState.falsePositives++;
      log(`Response: ${JSON.stringify(res.info)} - Penalty applied.`, 'error');
    } else {
      log(`Response: ${JSON.stringify(res.info)}`, 'info');
    }
    
    // Sync graph state visually
    buildGraphData(currentState.networkSummary, currentState.alarms);
    updateUI();

    if (res.done) {
      clearInterval(timerInterval);
      log('Mission completed.', 'info');
      await evaluateEpisode();
    }
  } catch (err) {
    log(`Action failed: ${err.message}`, 'error');
  }
}

async function evaluateEpisode() {
  els.endModal.classList.remove('hidden');
  const elapsed = Math.max(1, Math.floor((Date.now() - startTime) / 1000));
  
  try {
    const state = await fetch(`${API_BASE}/state?task=${currentState.task}`).then(r=>r.json());
    
    const traj = {
      root_cause_fixed: state.root_cause_fixed,
      steps_taken: state.steps_taken,
      false_positives: state.false_positives,
      elapsed_seconds: elapsed
    };
    
    const grade = await apiPost('/grade', { task: currentState.task, trajectory: traj });
    
    document.getElementById('finalScore').innerText = grade.score.toFixed(4);
    document.getElementById('tdRootCause').innerText = state.root_cause_id || '--';
    document.getElementById('tdF1').innerText = grade.breakdown.f1_score.toFixed(4);
    document.getElementById('tdEfficiency').innerText = grade.breakdown.efficiency_mult.toFixed(4);
    document.getElementById('tdSpeed').innerText = `+${grade.breakdown.speed_bonus.toFixed(4)}`;
    document.getElementById('tdFP').innerText = currentState.falsePositives;
    
    if (grade.score > 0.8) {
      document.getElementById('modalTitle').innerText = 'Mission Accomplished';
      document.getElementById('modalTitle').style.color = 'var(--status-up)';
    } else {
      document.getElementById('modalTitle').innerText = 'Mission Failed';
      document.getElementById('modalTitle').style.color = 'var(--status-failed)';
    }
  } catch(e) {
    log('Failed to fetch final grade', 'error');
  }
}

window.closeModal = function() {
  els.endModal.classList.add('hidden');
}
