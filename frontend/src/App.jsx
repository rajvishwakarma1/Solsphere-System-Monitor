import React, { useEffect, useState } from "react";
import axios from "axios";
import './App.css';

const API = "http://localhost:5000/machines";

export default function App() {
  // ---------------------- State ----------------------
  const [machines, setMachines] = useState([]);
  const [osFilter, setOsFilter] = useState("");
  const [machineQuery, setMachineQuery] = useState("");
  const [onlyIssues, setOnlyIssues] = useState(false);
  const [issueType, setIssueType] = useState(""); // '', 'disk', 'update', 'antivirus', 'sleep'
  const [sort, setSort] = useState({ key: 'timestamp', dir: 'desc' });

  // ---------------------- Data Fetch ----------------------
  const fetchData = () => {
    axios.get(API, { params: { os: osFilter } })
      .then(res => setMachines(res.data));
  };

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 10000); // Auto-refresh every 10 seconds
    return () => clearInterval(timer);
  }, [osFilter]);


  // Format sleep value as minutes
  const formatSleep = (m) => {
    const v = m?.sleep_settings?.timeout_minutes;
    const num = Number(v);
    return Number.isFinite(num) ? `${Math.round(num)}` : (v != null ? String(v) : '-');
  };

  // Zero-padding helper for timestamps and CSV
  const pad = (n) => String(n).padStart(2, '0');

  // Convert ISO timestamp to readable local format
  const formatLocal = (isoTs) => {
    if (!isoTs) return '-';
    const d = new Date(isoTs);
    if (isNaN(d.getTime())) return String(isoTs);
    const M = d.getMonth() + 1;
    const D = d.getDate();
    const YYYY = d.getFullYear();
    let h = d.getHours();
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    const mm = pad(d.getMinutes());
    const ss = pad(d.getSeconds());
    return `${D}-${M}-${YYYY}, ${h}:${mm}:${ss} ${ampm}`;
  };

  // Display how long ago the last check-in was
  const formatRelative = (isoTs) => {
    if (!isoTs) return '-';
    const d = new Date(isoTs);
    const now = new Date();
    const diffMs = Math.max(0, now - d);
    const sec = Math.floor(diffMs / 1000);
    const min = Math.floor(sec / 60);
    const hr = Math.floor(min / 60);
    const day = Math.floor(hr / 24);
    if (day > 0) return `${day} day${day !== 1 ? 's' : ''} ago`;
    if (hr > 0) return `${hr} hour${hr !== 1 ? 's' : ''} ago`;
    if (min > 0) return `${min} min ago`;
    return `just now`;
  };

  // Case-insensitive search by machine ID
  const matchesMachine = (m) => {
    if (!machineQuery) return true;
    const q = machineQuery.toLowerCase();
    return (m?.machine_id || '').toLowerCase().includes(q);
  };

  // Identify if a machine has issues
  const withIssues = (m, type = "") => {
    const diskIssue = !m?.disk_encryption;
    const updateIssue = (m?.os_update?.latest || "").toLowerCase().includes("update available");
    const avIssue = !(m?.antivirus?.installed) || !(m?.antivirus?.active);
    const sleepVal = Number(m?.sleep_settings?.timeout_minutes);
    const sleepIssue = Number.isFinite(sleepVal) && sleepVal > 10;

    switch (type) {
      case 'disk': return diskIssue;
      case 'update': return updateIssue;
      case 'antivirus': return avIssue;
      case 'sleep': return sleepIssue;
      default: return diskIssue || updateIssue || avIssue || sleepIssue;
    }
  };

  // Filter and sort pipeline
  const filtered = machines.filter(matchesMachine);
  const filteredWithToggle = filtered.filter(m => (onlyIssues ? withIssues(m, issueType) : true));

  // Custom sort logic per column
  const getSortValue = (m, key) => {
    switch (key) {
      case 'machine_id': return (m?.machine_id || '').toLowerCase();
      case 'os': return (m?.os || '').toLowerCase();
      case 'disk_encryption': return m?.disk_encryption ? 1 : 0;
      case 'os_update': return (m?.os_update?.latest || '').toLowerCase();
      case 'antivirus': {
        const a = m?.antivirus;
        return (a?.installed && a?.active) ? 2 : (a?.installed ? 1 : 0);
      }
      case 'sleep': return Number(m?.sleep_settings?.timeout_minutes) || 0;
      case 'timestamp': return new Date(m?.timestamp || 0).getTime() || 0;
      default: return 0;
    }
  };

  const sorted = [...filteredWithToggle].sort((a, b) => {
    const va = getSortValue(a, sort.key);
    const vb = getSortValue(b, sort.key);
    if (va < vb) return sort.dir === 'asc' ? -1 : 1;
    if (va > vb) return sort.dir === 'asc' ? 1 : -1;
    return 0;
  });

  const onSort = (key) => {
    setSort((prev) =>
      prev.key === key ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }
    );
  };

  // ---------------------- UI Components ----------------------

  const Badge = ({ text, kind }) => (
    <span className={`badge ${kind || ''}`}>{text}</span>
  );

  const OsBadge = ({ os }) => {
    const t = os === 'Darwin' ? 'macOS' : (os || '-');
    return <Badge text={t} kind="badge-os" />;
  };

  const EncBadge = ({ ok }) => (
    <Badge text={ok ? 'Enabled' : 'Disabled'} kind={ok ? 'badge-green' : 'badge-red'} />
  );

  const UpdateBadge = ({ latest }) => {
    const txt = (latest || '').toLowerCase().includes('update available') ? 'Outdated' : 'Up-to-date';
    const ok = txt === 'Up-to-date';
    return <Badge text={txt} kind={ok ? 'badge-green' : 'badge-red'} />;
  };

  const AvBadge = ({ av }) => {
    const installed = !!av?.installed;
    const active = !!av?.active;
    let txt = 'Missing', kind = 'badge-red';
    if (installed && active) { txt = 'Active'; kind = 'badge-green'; }
    else if (installed) { txt = 'Inactive'; kind = 'badge-red'; }
    return <Badge text={txt} kind={kind} />;
  };

  const SleepBadge = ({ m }) => {
    const v = Number(m?.sleep_settings?.timeout_minutes) || 0;
    const bad = v > 10;
    return <span className={bad ? 'text-red' : ''}>{v} min</span>;
  };

  // ---------------------- Export to CSV ----------------------

  const exportCSV = () => {
    const headers = [
      'Machine ID', 'OS', 'Disk Encryption', 'OS Update Current', 'OS Update Latest',
      'Antivirus Installed', 'Antivirus Active', 'Sleep (min)', 'Last Check-in'
    ];
    const rows = sorted.map(m => [
      m?.machine_id ?? '',
      m?.os ?? '',
      m?.disk_encryption ? 'Yes' : 'No',
      m?.os_update?.current ?? '',
      m?.os_update?.latest ?? '',
      m?.antivirus?.installed ? 'yes' : 'no',
      m?.antivirus?.active ? 'yes' : 'no',
      formatSleep(m),
      formatLocal(m?.timestamp),
    ]);
    const csv = [headers, ...rows]
      .map(r => r.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const ts = new Date();
    a.href = url;
    a.download = `machines_${ts.getFullYear()}${pad(ts.getMonth() + 1)}${pad(ts.getDate())}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ---------------------- Render UI ----------------------

  return (
    <div style={{ padding: "20px" }}>
      <div className="navbar topbar">
        <div className="brand">
          <div className="logo" aria-hidden>🛡️</div>
          <div className="title">ADMIN DASHBOARD</div>
        </div>
      </div>

      <h2 className="section-title">Machine Health Overview</h2>

      <div className="toolbar">
        <span className="muted">Filter by OS</span>
        <select value={osFilter} onChange={e => setOsFilter(e.target.value)}>
          <option value="">All OS</option>
          <option value="Windows">Windows</option>
          <option value="Darwin">macOS</option>
          <option value="Linux">Linux</option>
        </select>

        <label className="toggle">
          <input
            type="checkbox"
            checked={onlyIssues}
            onChange={e => setOnlyIssues(e.target.checked)}
          /> Show only machines with issues
        </label>

        <select
          value={issueType}
          onChange={(e) => setIssueType(e.target.value)}
          disabled={!onlyIssues}
          className="os-select"
          style={{ minWidth: '200px' }}
          aria-label="Issue type filter"
        >
          <option value="">All Issues</option>
          <option value="disk">Disk Encryption Off</option>
          <option value="update">Update Pending</option>
          <option value="antivirus">Antivirus Issue</option>
          <option value="sleep">Sleep &gt; 10 min</option>
        </select>

        <input
          type="text"
          placeholder="Search machine id"
          value={machineQuery}
          onChange={e => setMachineQuery(e.target.value)}
          className="search"
        />

        <div className="spacer" />
        <div className="stats-inline">
          Total: {sorted.length} | With issues: {sorted.filter(m => withIssues(m, issueType)).length}
        </div>
      </div>

      <div className="table-header">
        <div className="table-actions">
          <button className="btn" onClick={fetchData}>Refresh</button>
          <button className="btn" onClick={exportCSV}>Export CSV</button>
        </div>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th onClick={() => onSort('machine_id')}>Machine ID</th>
              <th onClick={() => onSort('os')}>Operating System</th>
              <th onClick={() => onSort('disk_encryption')}>Disk Encryption Status</th>
              <th onClick={() => onSort('os_update')}>OS Update Status</th>
              <th onClick={() => onSort('antivirus')}>Antivirus Status</th>
              <th onClick={() => onSort('sleep')}>Sleep Timeout</th>
              <th onClick={() => onSort('timestamp')}>Last Check-in</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((m, i) => (
              <tr key={i} className={withIssues(m) ? 'row-issue' : ''}>
                <td>{m?.machine_id}</td>
                <td><OsBadge os={m?.os} /></td>
                <td><EncBadge ok={m?.disk_encryption} /></td>
                <td><UpdateBadge latest={m?.os_update?.latest} /></td>
                <td><AvBadge av={m?.antivirus} /></td>
                <td><SleepBadge m={m} /></td>
                <td>{formatRelative(m?.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
