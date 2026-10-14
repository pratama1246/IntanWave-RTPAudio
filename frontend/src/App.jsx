import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  ChevronDown, Play, Square, Volume2, Radio, Clock, Music, 
  Upload, Trash2, Settings, Plus, RefreshCw, Bell, 
  Siren, HardHat, Copy, History, X, Search, 
  Wifi, Activity, Check,
  Headphones, Pause,
  Layers, Edit2, AlertTriangle, ArrowRight, Laptop
} from 'lucide-react';

const DAYS_CONFIG = [
  { key: 'mon', label: 'Sen', full: 'Senin' },
  { key: 'tue', label: 'Sel', full: 'Selasa' },
  { key: 'wed', label: 'Rab', full: 'Rabu' },
  { key: 'thu', label: 'Kam', full: 'Kamis' },
  { key: 'fri', label: 'Jum', full: 'Jumat' },
  { key: 'sat', label: 'Sab', full: 'Sabtu' },
  { key: 'sun', label: 'Min', full: 'Minggu' },
];

// REUSABLE UNIFIED CUSTOM DROPDOWN COMPONENT (CLEAN, MODERN, CONSISTENT)
function CustomDropdown({
  value,
  onChange,
  options,
  variant = 'light', // 'light' | 'dark'
  placeholder = 'Pilih...',
  className = '',
  buttonClassName = '',
  menuClassName = '',
  size = 'md'
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const safeOptions = Array.isArray(options) ? options : [];
  const selectedOption = safeOptions.find(opt => opt && String(opt.value) === String(value));
  const isDark = variant === 'dark';

  return (
    <div className={`relative inline-block ${className}`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center justify-between gap-2 rounded-xl transition-all font-medium text-xs cursor-pointer outline-hidden select-none ${
          size === 'sm' ? 'px-2.5 py-1.5' : 'px-3 py-2'
        } ${
          isDark
            ? 'bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 hover:border-slate-600 focus:ring-1 focus:ring-blue-400 shadow-xs'
            : 'bg-slate-50 text-slate-700 border border-slate-200 hover:bg-white hover:border-slate-300 focus:ring-2 focus:ring-blue-500/20 shadow-2xs'
        } ${buttonClassName}`}
      >
        <span className="truncate flex items-center gap-1.5">
          {selectedOption?.icon}
          <span>{selectedOption ? selectedOption.label : placeholder}</span>
        </span>
        <ChevronDown className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 ${
          isDark ? 'text-slate-400' : 'text-slate-500'
        } ${isOpen ? 'rotate-180 text-blue-400' : ''}`} />
      </button>

      {isOpen && (
        <div
          className={`absolute left-0 top-full mt-1.5 min-w-full max-h-60 overflow-y-auto rounded-xl p-1 z-50 shadow-xl border animate-in fade-in zoom-in-95 duration-100 ${
            isDark
              ? 'bg-slate-800 border-slate-700 text-slate-200 divide-y divide-slate-700/50'
              : 'bg-white border-slate-200 text-slate-700 divide-y divide-slate-100'
          } ${menuClassName}`}
          style={{ minWidth: 'max-content' }}
        >
          <div className="py-0.5 space-y-0.5">
            {safeOptions.map((option) => {
              const isSelected = String(option.value) === String(value);
              return (
                <button
                  key={String(option.value)}
                  type="button"
                  onClick={() => {
                    onChange(option.value);
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-center justify-between gap-3 px-3 py-1.5 rounded-lg text-xs text-left transition-colors cursor-pointer ${
                    isSelected
                      ? isDark
                        ? 'bg-blue-600/20 text-blue-400 font-semibold'
                        : 'bg-blue-50 text-blue-700 font-semibold'
                      : isDark
                        ? 'hover:bg-slate-700/70 text-slate-300 hover:text-white'
                        : 'hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <div className="min-w-0">
                    <div className="truncate flex items-center gap-1.5">
                      {option.icon}
                      <span>{option.label}</span>
                    </div>
                    {option.sublabel && (
                      <span className="block text-[10px] text-slate-400 truncate mt-0.5">
                        {option.sublabel}
                      </span>
                    )}
                  </div>
                  {isSelected && (
                    <Check className={`w-3.5 h-3.5 shrink-0 ml-2 ${
                      isDark ? 'text-blue-400' : 'text-blue-600'
                    }`} />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  // Playback state (Field / Server Broadcast)
  const [playback, setPlayback] = useState({
    status: 'IDLE',
    title: 'Siaga untuk siaran',
    file: '',
    duration: 0,
    elapsed: 0,
    enable_multicast: true,
    enable_local: true,
    multicast_dest: '239.255.0.1:5004',
    target_desc: 'Semua Speaker (Multicast)'
  });

  const [audioList, setAudioList] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [speakers, setSpeakers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [currentTime, setCurrentTime] = useState('');
  const [wsConnected, setWsConnected] = useState(false);

  // Local Browser Audio Preview State (HTML5 Audio, DOES NOT broadcast outside)
  const localAudioRef = useRef(new Audio());
  const [previewingId, setPreviewingId] = useState(null);
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false);

  // Broadcast Target Selection State
  const [targetMode, setTargetMode] = useState('all'); // 'all', 'group', 'speaker'
  const [selectedGroup, setSelectedGroup] = useState('Kantor');
  const [selectedSpeakerId, setSelectedSpeakerId] = useState(null);
  const [selectedSpeakerIds, setSelectedSpeakerIds] = useState([]);


  // Monitoring Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'online', 'offline'
  const [groupFilter, setGroupFilter] = useState('all');
  const [isScanning, setIsScanning] = useState(false);
  const [testingSpeakerId, setTestingSpeakerId] = useState(null);
  const [pingingSpeakerId, setPingingSpeakerId] = useState(null);
  const [copiedSpeakerId, setCopiedSpeakerId] = useState(null);

  // Modals & Navigation
  const [activeMainTab, setActiveMainTab] = useState('schedules'); // 'schedules' | 'audio'
  const [showSpeakerMonitorModal, setShowSpeakerMonitorModal] = useState(false);
  const [showAddSchedule, setShowAddSchedule] = useState(false);
  const [editingScheduleId, setEditingScheduleId] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showLogsModal, setShowLogsModal] = useState(false);
  const [showSpeakerModal, setShowSpeakerModal] = useState(false);
  const [showSirenConfirmModal, setShowSirenConfirmModal] = useState(false);
  const [editingSpeaker, setEditingSpeaker] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  // Audio Upload & Category State (Biasa vs Darurat)
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadSelectedFile, setUploadSelectedFile] = useState(null);
  const [uploadDisplayName, setUploadDisplayName] = useState('');
  const [uploadCategory, setUploadCategory] = useState('biasa'); // 'biasa' | 'darurat'
  const [audioCategoryFilter, setAudioCategoryFilter] = useState('all'); // 'all' | 'biasa' | 'darurat'
  const [selectedEmergencyAudio, setSelectedEmergencyAudio] = useState('');
  const [categoryChangeTarget, setCategoryChangeTarget] = useState(null);
  const [editingDisplayName, setEditingDisplayName] = useState('');

  // Group Management State
  const [groups, setGroups] = useState([]);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [editingGroupOldName, setEditingGroupOldName] = useState(null);
  const [editingGroupNewName, setEditingGroupNewName] = useState('');

  // Speaker Form State
  const [speakerForm, setSpeakerForm] = useState({
    name: '',
    ip_address: '',
    port: 5004,
    groups: ['Kantor'],
    groupsText: 'Kantor',
    zone: 'Kantor',
    device_type: 'physical'
  });
  const [modalPingStatus, setModalPingStatus] = useState({ testing: false, result: null });

  // Settings State
  const [settings, setSettings] = useState({
    multicast_ip: '239.255.0.1',
    multicast_port: '5004',
    enable_multicast: 'true',
    enable_local: 'true'
  });

  // Schedule form state
  const [newSchedule, setNewSchedule] = useState({
    name: '',
    audio_file_id: '',
    schedule_type: 'daily',
    time_str: '08:00',
    days_of_week: 'mon,tue,wed,thu,fri',
    target_mode: 'all',
    target_group: '',
    target_zone: '',
    target_speaker_id: 0,
    target_multicast: true,
    target_local: true
  });
  const [scheduleTimeInput, setScheduleTimeInput] = useState('08:00');

  // Multi-Time Helpers for Schedule
  const parseScheduleTimes = (timeStr) => {
    if (!timeStr) return ['08:00'];
    const parts = timeStr.split(',').map(t => t.trim()).filter(Boolean);
    return parts.length > 0 ? parts : ['08:00'];
  };

  const handleAddTime = () => {
    if (!scheduleTimeInput) return;
    const current = parseScheduleTimes(newSchedule.time_str);
    if (!current.includes(scheduleTimeInput)) {
      const updated = [...current, scheduleTimeInput].sort();
      setNewSchedule(prev => ({ ...prev, time_str: updated.join(', ') }));
    }
  };

  const handleAddPresetTime = (presetTime) => {
    const current = parseScheduleTimes(newSchedule.time_str);
    if (!current.includes(presetTime)) {
      const updated = [...current, presetTime].sort();
      setNewSchedule(prev => ({ ...prev, time_str: updated.join(', ') }));
    }
  };

  const handleRemoveTime = (timeToRemove) => {
    const current = parseScheduleTimes(newSchedule.time_str);
    if (current.length <= 1) {
      alert('Jadwal harus memiliki minimal 1 jam siaran');
      return;
    }
    const updated = current.filter(t => t !== timeToRemove);
    setNewSchedule(prev => ({ ...prev, time_str: updated.join(', ') }));
  };

  const fileInputRef = useRef(null);

  // Realtime clock
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' WIB');
    };
    updateClock();
    const timer = setInterval(updateClock, 1000);
    return () => clearInterval(timer);
  }, []);

  // Browser Audio Event Listeners
  useEffect(() => {
    const audio = localAudioRef.current;
    const handleEnded = () => {
      setIsPreviewPlaying(false);
      setPreviewingId(null);
    };
    const handlePause = () => {
      setIsPreviewPlaying(false);
    };
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('pause', handlePause);

    return () => {
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('pause', handlePause);
      audio.pause();
    };
  }, []);

  // Fetch initial data
  const fetchData = async () => {
    try {
      const [resAudio, resSched, resSet, resLogs, resSpeakers, resGroups] = await Promise.all([
        fetch('/api/audio').then(r => r.json()),
        fetch('/api/schedules').then(r => r.json()),
        fetch('/api/settings').then(r => r.json()),
        fetch('/api/logs').then(r => r.json()),
        fetch('/api/speakers').then(r => r.json()),
        fetch('/api/groups').then(r => r.json()).catch(() => fetch('/api/zones').then(r => r.json()).catch(() => []))
      ]);
      setAudioList(resAudio || []);
      setSchedules(resSched || []);
      setSettings(resSet || {});
      setLogs(resLogs || []);
      setSpeakers(resSpeakers || []);
      setGroups(resGroups || []);

      if (resAudio && resAudio.length > 0 && !newSchedule.audio_file_id) {
        setNewSchedule(prev => ({ ...prev, audio_file_id: resAudio[0].id }));
      }
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  };

  const fetchGroups = async () => {
    try {
      const res = await fetch('/api/groups');
      if (res.ok) {
        const data = await res.json();
        setGroups(data);
      }
    } catch (err) {
      console.error('Failed to fetch groups', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // WebSocket Live Telemetry
  useEffect(() => {
    let ws;
    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connectWs, 2000);
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'speakers_update' && Array.isArray(data.speakers)) {
            setSpeakers(data.speakers);
          } else if (data.type === 'groups_update' && Array.isArray(data.groups)) {
            setGroups(data.groups);
          } else if (data.type === 'zones_update' && Array.isArray(data.zones)) {
            setGroups(data.zones);
          } else if (data.status) {
            setPlayback(data);
          }
        } catch (e) {}
      };
    };

    connectWs();
    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Play / Stop Browser Local Preview (Dashboard only, ZERO broadcast to outside)
  const handleBrowserPreview = (url, identifier) => {
    const audio = localAudioRef.current;
    if (previewingId === identifier && isPreviewPlaying) {
      audio.pause();
      setIsPreviewPlaying(false);
      setPreviewingId(null);
      return;
    }

    audio.src = url;
    audio.play().then(() => {
      setIsPreviewPlaying(true);
      setPreviewingId(identifier);
    }).catch(e => {
      console.error('Browser preview error:', e);
      setIsPreviewPlaying(false);
      setPreviewingId(null);
    });
  };

  const handleStopBrowserPreview = () => {
    const audio = localAudioRef.current;
    audio.pause();
    audio.currentTime = 0;
    setIsPreviewPlaying(false);
    setPreviewingId(null);
  };

  // Helper ambil daftar groups dari speaker
  const getSpeakerGroups = (s) => {
    if (!s) return [];
    if (Array.isArray(s.groups) && s.groups.length > 0) return s.groups;
    if (s.zone) return [s.zone];
    return ['Kantor'];
  };

  // Unique Groups list from groups table and speakers
  const groupsList = useMemo(() => {
    const set = new Set();
    groups.forEach(g => g && g.name && set.add(g.name.trim()));
    speakers.forEach(s => {
      const grps = getSpeakerGroups(s);
      grps.forEach(g => g && set.add(g.trim()));
    });
    return Array.from(set).filter(Boolean);
  }, [groups, speakers]);

  // Audio list filtered by category
  const filteredAudioList = useMemo(() => {
    if (audioCategoryFilter === 'all') return audioList;
    return audioList.filter(a => (a.category || 'biasa') === audioCategoryFilter);
  }, [audioList, audioCategoryFilter]);

  // Emergency audios
  const emergencyAudios = useMemo(() => {
    return audioList.filter(a => a.category === 'darurat');
  }, [audioList]);

  // Online count
  const onlineCount = useMemo(() => {
    return speakers.filter(s => s.status === 'online').length;
  }, [speakers]);

  // Filtered speakers list
  const filteredSpeakers = useMemo(() => {
    return speakers.filter(s => {
      const q = searchQuery.toLowerCase().trim();
      const sGroups = getSpeakerGroups(s);
      const matchesSearch = !q || 
        s.name.toLowerCase().includes(q) || 
        s.ip_address.toLowerCase().includes(q) || 
        sGroups.some(g => g.toLowerCase().includes(q));

      const matchesStatus = 
        statusFilter === 'all' ||
        (statusFilter === 'online' && s.status === 'online') ||
        (statusFilter === 'offline' && s.status !== 'online');

      const matchesGroup = 
        groupFilter === 'all' || sGroups.includes(groupFilter);

      return matchesSearch && matchesStatus && matchesGroup;
    });
  }, [speakers, searchQuery, statusFilter, groupFilter]);

  // Target summary calculation for Broadcast
  const targetSummaryText = useMemo(() => {
    if (targetMode === 'all') {
      return `Semua Speaker (${speakers.length} terdaftar • ${onlineCount} online)`;
    }
    if (targetMode === 'group' || targetMode === 'zone') {
      const grpSpeakers = speakers.filter(s => getSpeakerGroups(s).includes(selectedGroup));
      const onCount = grpSpeakers.filter(s => s.status === 'online').length;
      return `Group: ${selectedGroup} (${grpSpeakers.length} speaker • ${onCount} online)`;
    }
    if (targetMode === 'speaker') {
      const sp = speakers.find(s => s.id === selectedSpeakerId);
      if (sp) {
        return `Speaker ${sp.name} (${sp.status === 'online' ? 'Online' : 'Offline'})`;
      }
    }
    return 'Semua Speaker';
  }, [targetMode, selectedGroup, selectedSpeakerId, speakers, onlineCount]);

  // Direct Target Options: Hanya menampilkan Semua Speaker, Group yang memiliki speaker terdaftar, dan Speaker tunggal
  const targetOptions = useMemo(() => {
    const list = [
      { value: 'all', label: 'Semua Speaker' }
    ];

    // Hanya tampilkan group yang benar-benar memiliki speaker terdaftar!
    const activeGroupsWithSpeakers = groupsList.filter(g => 
      speakers.some(s => getSpeakerGroups(s).map(x => x.toLowerCase()).includes(g.toLowerCase()))
    );

    activeGroupsWithSpeakers.forEach((g) => {
      const spkCount = speakers.filter(s => 
        getSpeakerGroups(s).map(x => x.toLowerCase()).includes(g.toLowerCase())
      ).length;
      list.push({
        value: `group:${g}`,
        label: `Group: ${g} (${spkCount} Speaker)`
      });
    });

    speakers.forEach((s) => {
      list.push({
        value: `speaker:${s.id}`,
        label: `Speaker: ${s.name} (${s.ip_address})`
      });
    });

    return list;
  }, [groupsList, speakers]);

  const currentTargetValue = useMemo(() => {
    if (targetMode === 'group' || targetMode === 'zone') return `group:${selectedGroup}`;
    if (targetMode === 'speaker') return `speaker:${selectedSpeakerId}`;
    return 'all';
  }, [targetMode, selectedGroup, selectedSpeakerId]);

  const handleTargetChange = (val) => {
    if (val === 'all') {
      setTargetMode('all');
    } else if (val.startsWith('group:') || val.startsWith('zone:')) {
      const grpName = val.replace(/^(group:|zone:)/, '');
      setTargetMode('group');
      setSelectedGroup(grpName);
    } else if (val.startsWith('speaker:')) {
      const spId = parseInt(val.replace('speaker:', ''), 10);
      setTargetMode('speaker');
      setSelectedSpeakerId(spId);
    }
  };

  // Calculate Next Upcoming Alarm based on schedule_type and days_of_week
  const getNextScheduleInfo = () => {
    const active = schedules.filter(s => s.enabled);
    if (active.length === 0) return null;

    const now = new Date();
    const DAY_CODES = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    const DAY_LABELS_INDO = {
      sun: 'Minggu',
      mon: 'Senin',
      tue: 'Selasa',
      wed: 'Rabu',
      thu: 'Kamis',
      fri: 'Jumat',
      sat: 'Sabtu'
    };

    const candidates = [];

    for (const s of active) {
      // Tentukan hari apa saja jadwal ini diizinkan berjalan
      let allowedDays = [];
      const stype = s.schedule_type || 'daily';
      if (stype === 'daily') {
        allowedDays = [...DAY_CODES];
      } else if (stype === 'weekdays') {
        allowedDays = ['mon', 'tue', 'wed', 'thu', 'fri'];
      } else if (stype === 'once') {
        allowedDays = [...DAY_CODES];
      } else {
        // custom / days
        if (s.days_of_week) {
          allowedDays = s.days_of_week.split(',').map(d => d.trim().toLowerCase()).filter(Boolean);
        }
        if (allowedDays.length === 0) {
          allowedDays = ['mon', 'tue', 'wed', 'thu', 'fri'];
        }
      }

      // Dukung multi-waktu per jadwal (misal: "08:00, 11:00, 15:00")
      const timesList = parseScheduleTimes(s.time_str);

      for (const tStr of timesList) {
        const parts = tStr.split(':');
        const h = parseInt(parts[0], 10) || 0;
        const m = parseInt(parts[1], 10) || 0;

        // Cari waktu eksekusi terdekat (hari ini s.d. 7 hari ke depan)
        for (let offset = 0; offset <= 7; offset++) {
          const candidateDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset, h, m, 0, 0);
          const dayCode = DAY_CODES[candidateDate.getDay()];

          if (allowedDays.includes(dayCode) && candidateDate.getTime() > now.getTime()) {
            const diffMs = candidateDate.getTime() - now.getTime();
            const diffMinutes = Math.floor(diffMs / 60000);

            let dayLabel = 'Hari ini';
            if (offset === 1) {
              dayLabel = 'Besok';
            } else if (offset > 1) {
              dayLabel = DAY_LABELS_INDO[dayCode] || dayCode;
            }

            const days = Math.floor(diffMinutes / (24 * 60));
            const hours = Math.floor((diffMinutes % (24 * 60)) / 60);
            const mins = diffMinutes % 60;
            const countdown = days > 0
              ? `${days}h ${hours}j ${mins}m`
              : `${hours}j ${mins}m`;

            candidates.push({
              ...s,
              time_str: tStr, // Jam spesifik yang akan aktif
              diff: diffMinutes,
              nextDate: candidateDate,
              dayLabel,
              countdown,
              isTomorrow: offset === 1
            });
            break; // Temukan hari terdekat untuk jam spesifik ini
          }
        }
      }
    }

    if (candidates.length === 0) return null;
    candidates.sort((a, b) => a.diff - b.diff);
    return candidates[0];
  };

  const nextSchedule = getNextScheduleInfo();

  // Helper build target payload for server broadcast
  const buildTargetPayload = () => {
    return {
      target_mode: (targetMode === 'group' || targetMode === 'zone') ? 'group' : targetMode,
      target_group: (targetMode === 'group' || targetMode === 'zone') ? selectedGroup : null,
      target_zone: (targetMode === 'group' || targetMode === 'zone') ? selectedGroup : null,
      speaker_id: targetMode === 'speaker' ? selectedSpeakerId : null
    };
  };

  // Play audio to Outside Physical Speakers (Server Broadcast)
  const handlePlayToSpeakers = async (audioId) => {
    handleStopBrowserPreview();
    try {
      const payload = { audio_id: audioId, enable_local: false, ...buildTargetPayload() };
      const res = await fetch('/api/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        alert('Gagal menyiarkan audio: ' + (errData.detail || res.statusText || 'Server Error'));
      }
      fetchData();
    } catch (err) {
      alert('Gagal menyiarkan audio: ' + err);
    }
  };

  // Play audio filename to Outside Physical Speakers
  const handlePlayFilenameToSpeakers = async (filename) => {
    handleStopBrowserPreview();
    try {
      const payload = { filename, enable_local: false, ...buildTargetPayload() };
      const res = await fetch('/api/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        alert('Gagal menyiarkan ke speaker: ' + (errData.detail || res.statusText || 'Server Error'));
      }
      fetchData();
    } catch (err) {
      alert('Gagal menyiarkan ke speaker: ' + err);
    }
  };

  // Stop Field Broadcast
  const handleStop = async () => {
    try {
      await fetch('/api/stop', { method: 'POST' });
      fetchData();
    } catch (err) {
      alert('Gagal menghentikan siaran: ' + err);
    }
  };

  // Trigger Scan All Speakers
  const handleScanAll = async () => {
    setIsScanning(true);
    try {
      const res = await fetch('/api/speakers/scan', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.speakers) setSpeakers(data.speakers);
      }
    } catch (err) {
      console.error('Scan error:', err);
    } finally {
      setIsScanning(false);
    }
  };

  // Test Single Outside Physical Speaker
  const handleTestPhysicalSpeaker = async (speaker) => {
    handleStopBrowserPreview();
    setTestingSpeakerId(speaker.id);
    try {
      await fetch(`/api/speakers/${speaker.id}/test-audio`, { method: 'POST' });
    } catch (err) {
      alert(`Gagal tes suara ke ${speaker.name}: ${err}`);
    } finally {
      setTimeout(() => setTestingSpeakerId(null), 2500);
    }
  };

  // Ping Single Speaker
  const handlePingSpeaker = async (speaker) => {
    setPingingSpeakerId(speaker.id);
    try {
      const res = await fetch(`/api/speakers/${speaker.id}/ping`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSpeakers(prev => prev.map(s => s.id === speaker.id ? (data.speaker || s) : s));
      }
    } catch (err) {
      console.error('Ping error:', err);
    } finally {
      setPingingSpeakerId(null);
    }
  };

  // Copy IP to Clipboard
  const handleCopyIp = (id, ip) => {
    navigator.clipboard.writeText(ip);
    setCopiedSpeakerId(id);
    setTimeout(() => setCopiedSpeakerId(null), 1500);
  };

  // Open Add Speaker Modal
  const handleOpenAddSpeaker = () => {
    setEditingSpeaker(null);
    const defaultGrp = groupsList[0] || 'Kantor';
    setSpeakerForm({
      name: '',
      ip_address: '',
      port: 5004,
      groups: [defaultGrp],
      groupsText: defaultGrp,
      zone: defaultGrp,
      device_type: 'physical'
    });
    setModalPingStatus({ testing: false, result: null });
    setShowSpeakerModal(true);
  };

  // Open Edit Speaker Modal
  const handleOpenEditSpeaker = (speaker) => {
    setEditingSpeaker(speaker);
    const grps = getSpeakerGroups(speaker);
    const textVal = grps.join(', ');
    setSpeakerForm({
      name: speaker.name,
      ip_address: speaker.ip_address,
      port: speaker.port || 5004,
      groups: grps,
      groupsText: textVal,
      zone: grps[0] || 'Kantor',
      device_type: speaker.device_type || 'physical'
    });
    setModalPingStatus({ testing: false, result: null });
    setShowSpeakerModal(true);
  };

  // Toggle group selection badge in speaker form
  const toggleSpeakerFormGroup = (groupName) => {
    const raw = speakerForm.groupsText || '';
    const current = raw.split(',').map(g => g.trim()).filter(Boolean);
    const lower = groupName.trim().toLowerCase();
    let next;
    if (current.some(g => g.toLowerCase() === lower)) {
      next = current.filter(g => g.toLowerCase() !== lower);
    } else {
      next = [...current, groupName.trim()];
    }
    setSpeakerForm(prev => ({
      ...prev,
      groupsText: next.join(', '),
      groups: next,
      zone: next[0] || 'Kantor'
    }));
  };

  // Test Ping from inside Modal
  const handleTestModalPing = async () => {
    if (!speakerForm.ip_address) return;
    setModalPingStatus({ testing: true, result: null });
    try {
      if (editingSpeaker) {
        const res = await fetch(`/api/speakers/${editingSpeaker.id}/ping`, { method: 'POST' });
        const data = await res.json();
        setModalPingStatus({ 
          testing: false, 
          result: { online: data.online, latency: data.latency_ms } 
        });
      } else {
        const res = await fetch('/api/speakers/scan', { method: 'POST' });
        const data = await res.json();
        const found = (data.speakers || []).find(s => s.ip_address === speakerForm.ip_address);
        setModalPingStatus({ 
          testing: false, 
          result: found ? { online: found.status === 'online', latency: found.latency_ms } : { online: false, latency: 0 } 
        });
      }
    } catch (err) {
      setModalPingStatus({ testing: false, result: { online: false, latency: 0 } });
    }
  };

  // Save Speaker (Create / Update)
  const handleSaveSpeaker = async (e) => {
    e.preventDefault();
    try {
      const parsedGrps = (speakerForm.groupsText || '')
        .split(',')
        .map(g => g.trim())
        .filter(Boolean);
      const finalGroups = parsedGrps.length > 0 ? parsedGrps : ['Kantor'];
      const payload = {
        name: speakerForm.name,
        ip_address: speakerForm.ip_address,
        port: speakerForm.port || 5004,
        groups: finalGroups,
        group: finalGroups[0],
        zone: finalGroups[0],
        device_type: speakerForm.device_type || 'physical'
      };

      if (editingSpeaker) {
        await fetch(`/api/speakers/${editingSpeaker.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetch('/api/speakers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      setShowSpeakerModal(false);
      fetchData();
    } catch (err) {
      alert('Gagal menyimpan speaker: ' + err);
    }
  };

  // Delete Speaker
  const handleDeleteSpeaker = async (id, name) => {
    if (!confirm(`Hapus speaker '${name}'?`)) return;
    try {
      await fetch(`/api/speakers/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (err) {
      alert('Gagal menghapus speaker: ' + err);
    }
  };

  // Toggle Custom Speaker selection
  const handleToggleSelectSpeaker = (id) => {
    setSelectedSpeakerIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  // Toggle Schedule
  const handleToggleSchedule = async (id) => {
    try {
      await fetch(`/api/schedules/${id}/toggle`, { method: 'PATCH' });
      fetchData();
    } catch (err) {
      alert('Gagal mengubah jadwal: ' + err);
    }
  };

  // Add Schedule
  const handleOpenAddSchedule = () => {
    setEditingScheduleId(null);
    setNewSchedule({
      name: '',
      audio_file_id: audioList[0]?.id || '',
      schedule_type: 'daily',
      time_str: '08:00',
      days_of_week: 'mon,tue,wed,thu,fri',
      target_mode: 'all',
      target_group: '',
      target_zone: '',
      target_speaker_id: 0,
      target_multicast: true,
      target_local: true
    });
    setScheduleTimeInput('08:00');
    setShowAddSchedule(true);
  };

  // Edit Schedule
  const handleOpenEditSchedule = (schedule) => {
    setEditingScheduleId(schedule.id);
    const existingTimes = parseScheduleTimes(schedule.time_str);
    setNewSchedule({
      name: schedule.name,
      audio_file_id: schedule.audio_file_id || (audioList[0]?.id || ''),
      schedule_type: schedule.schedule_type || 'daily',
      time_str: schedule.time_str || '08:00',
      days_of_week: schedule.days_of_week || 'mon,tue,wed,thu,fri',
      target_mode: schedule.target_mode || 'all',
      target_group: schedule.target_group || schedule.target_zone || '',
      target_zone: schedule.target_group || schedule.target_zone || '',
      target_speaker_id: schedule.target_speaker_id || 0,
      target_multicast: Boolean(schedule.target_multicast),
      target_local: Boolean(schedule.target_local)
    });
    setScheduleTimeInput(existingTimes[0] || '08:00');
    setShowAddSchedule(true);
  };

  // Duplicate Schedule
  const handleDuplicateSchedule = (schedule) => {
    setEditingScheduleId(null);
    const existingTimes = parseScheduleTimes(schedule.time_str);
    setNewSchedule({
      name: schedule.name + ' Salinan',
      audio_file_id: schedule.audio_file_id || (audioList[0]?.id || ''),
      schedule_type: schedule.schedule_type || 'daily',
      time_str: schedule.time_str || '08:00',
      days_of_week: schedule.days_of_week || 'mon,tue,wed,thu,fri',
      target_mode: schedule.target_mode || 'all',
      target_group: schedule.target_group || schedule.target_zone || '',
      target_zone: schedule.target_group || schedule.target_zone || '',
      target_speaker_id: schedule.target_speaker_id || 0,
      target_multicast: Boolean(schedule.target_multicast),
      target_local: Boolean(schedule.target_local)
    });
    setScheduleTimeInput(existingTimes[0] || '08:00');
    setShowAddSchedule(true);
  };

  // Delete Schedule
  const handleDeleteSchedule = async (id) => {
    if (!confirm('Hapus jadwal ini?')) return;
    try {
      await fetch(`/api/schedules/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (err) {
      alert('Gagal menghapus: ' + err);
    }
  };

  // Create or Update Schedule
  const handleSaveSchedule = async (e) => {
    e.preventDefault();
    try {
      if (editingScheduleId) {
        await fetch(`/api/schedules/${editingScheduleId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newSchedule)
        });
      } else {
        await fetch('/api/schedules', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newSchedule)
        });
      }
      setShowAddSchedule(false);
      setEditingScheduleId(null);
      fetchData();
    } catch (err) {
      alert('Gagal menyimpan jadwal: ' + err);
    }
  };

  // Audio Upload & Category Handlers
  const handleOpenUploadModal = (preselectedFile = null) => {
    if (preselectedFile) {
      setUploadSelectedFile(preselectedFile);
      const cleanName = preselectedFile.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' ');
      setUploadDisplayName(cleanName);
      const isEmerg = /siren|sirine|ews|darurat|emergency|bahaya|evakuasi/i.test(preselectedFile.name);
      setUploadCategory(isEmerg ? 'darurat' : 'biasa');
    } else {
      setUploadSelectedFile(null);
      setUploadDisplayName('');
      setUploadCategory('biasa');
    }
    setShowUploadModal(true);
  };

  const handleFilePickedForUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadSelectedFile(file);
    if (!uploadDisplayName) {
      const cleanName = file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' ');
      setUploadDisplayName(cleanName);
    }
    const isEmerg = /siren|sirine|ews|darurat|emergency|bahaya|evakuasi/i.test(file.name);
    if (isEmerg) setUploadCategory('darurat');
    setShowUploadModal(true);
    if (e.target) e.target.value = '';
  };

  const handleSubmitUpload = async (e) => {
    if (e) e.preventDefault();
    if (!uploadSelectedFile) {
      alert('Pilih berkas audio terlebih dahulu');
      return;
    }

    const formData = new FormData();
    formData.append('file', uploadSelectedFile);
    formData.append('display_name', uploadDisplayName.trim() || uploadSelectedFile.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '));
    formData.append('category', uploadCategory);

    setIsUploading(true);
    try {
      const res = await fetch('/api/audio/upload', {
        method: 'POST',
        body: formData
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Gagal unggah berkas');
      }
      setShowUploadModal(false);
      setUploadSelectedFile(null);
      setUploadDisplayName('');
      setUploadCategory('biasa');
      await fetchData();
    } catch (err) {
      alert('Gagal upload: ' + err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRequestChangeCategory = (audio, explicitTarget = null) => {
    const currentCat = audio.category || 'biasa';
    const targetCategory = explicitTarget || (currentCat === 'darurat' ? 'biasa' : 'darurat');
    setCategoryChangeTarget({ audio, targetCategory });
    setEditingDisplayName(audio.display_name || '');
  };

  const handleConfirmCategoryChange = async () => {
    if (!categoryChangeTarget) return;
    const { audio, targetCategory } = categoryChangeTarget;
    try {
      const res = await fetch(`/api/audio/${audio.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          category: targetCategory,
          display_name: editingDisplayName.trim() || audio.display_name
        })
      });
      if (res.ok) {
        setCategoryChangeTarget(null);
        fetchData();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Gagal memperbarui kategori audio');
      }
    } catch (err) {
      alert('Gagal menghubungi server');
    }
  };

  // Delete Audio
  const handleDeleteAudio = async (id) => {
    if (!confirm('Hapus berkas audio ini?')) return;
    try {
      await fetch(`/api/audio/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (err) {
      alert('Gagal menghapus: ' + err);
    }
  };

  // Save Settings
  const handleSaveSettings = async (e) => {
    e.preventDefault();
    try {
      await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      setShowSettings(false);
      fetchData();
    } catch (err) {
      alert('Gagal menyimpan pengaturan: ' + err);
    }
  };

  // Helper format seconds
  const formatSec = (seconds) => {
    if (!seconds) return '00:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Group Management Handlers
  const handleCreateGroup = async (e) => {
    if (e) e.preventDefault();
    const name = newGroupName.trim();
    if (!name) return;
    try {
      const res = await fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      if (res.ok) {
        setNewGroupName('');
        fetchGroups();
      } else {
        const err = await res.json();
        alert(err.detail || 'Gagal menambah group');
      }
    } catch (err) {
      alert('Gagal menghubungi server');
    }
  };

  const handleUpdateGroup = async (oldName, newName) => {
    const trimmed = (newName || '').trim();
    if (!trimmed || oldName === trimmed) {
      setEditingGroupOldName(null);
      return;
    }
    try {
      const res = await fetch(`/api/groups/${encodeURIComponent(oldName)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed })
      });
      if (res.ok) {
        setEditingGroupOldName(null);
        fetchGroups();
        fetchData();
      } else {
        const err = await res.json();
        alert(err.detail || 'Gagal mengubah group');
      }
    } catch (err) {
      alert('Gagal menghubungi server');
    }
  };

  const handleDeleteGroup = async (groupName) => {
    if (!confirm(`Hapus group "${groupName}"? Speaker di group ini akan dilepas dari group tersebut.`)) return;
    try {
      const res = await fetch(`/api/groups/${encodeURIComponent(groupName)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchGroups();
        fetchData();
      } else {
        const err = await res.json();
        alert(err.detail || 'Gagal menghapus group');
      }
    } catch (err) {
      alert('Gagal menghubungi server');
    }
  };

  // Schedule Day Selection Helpers
  const toggleScheduleDay = (dayKey) => {
    const raw = newSchedule.days_of_week || '';
    const current = raw.split(',').map(d => d.trim().toLowerCase()).filter(Boolean);
    let next;
    if (current.includes(dayKey)) {
      if (current.length <= 1) return; // minimal 1 hari aktif
      next = current.filter(d => d !== dayKey);
    } else {
      next = DAYS_CONFIG.filter(d => current.includes(d.key) || d.key === dayKey).map(d => d.key);
    }

    let nextType = 'custom';
    if (next.length === 7) nextType = 'daily';
    else if (next.length === 5 && ['mon','tue','wed','thu','fri'].every(d => next.includes(d))) nextType = 'weekdays';

    setNewSchedule(prev => ({
      ...prev,
      days_of_week: next.join(','),
      schedule_type: nextType
    }));
  };

  const setSchedulePreset = (preset) => {
    if (preset === 'daily') {
      setNewSchedule(prev => ({
        ...prev,
        schedule_type: 'daily',
        days_of_week: 'mon,tue,wed,thu,fri,sat,sun'
      }));
    } else if (preset === 'weekdays') {
      setNewSchedule(prev => ({
        ...prev,
        schedule_type: 'weekdays',
        days_of_week: 'mon,tue,wed,thu,fri'
      }));
    } else if (preset === 'weekends') {
      setNewSchedule(prev => ({
        ...prev,
        schedule_type: 'custom',
        days_of_week: 'sat,sun'
      }));
    }
  };

  // Helper relative schedule label
  const getScheduleLabel = (s) => {
    if (s.schedule_type === 'once') return 'Sekali jalan';
    if (s.schedule_type === 'interval') return `Tiap ${s.interval_hours || 2} jam`;

    const dow = s.days_of_week || '';
    const daysArr = dow.split(',').map(d => d.trim().toLowerCase()).filter(Boolean);

    if (daysArr.length === 7 || (!dow && s.schedule_type === 'daily')) {
      return 'Setiap hari';
    }
    if (daysArr.length === 5 && ['mon','tue','wed','thu','fri'].every(d => daysArr.includes(d))) {
      return 'Senin - Jumat';
    }
    if (daysArr.length === 2 && ['sat','sun'].every(d => daysArr.includes(d))) {
      return 'Sabtu & Minggu';
    }
    if (daysArr.length > 0) {
      const dayMap = { mon: 'Sen', tue: 'Sel', wed: 'Rab', thu: 'Kam', fri: 'Jum', sat: 'Sab', sun: 'Min' };
      return daysArr.map(d => dayMap[d] || d).join(', ');
    }
    return s.schedule_type === 'daily' ? 'Setiap hari' : s.schedule_type;
  };

  const isPlaying = playback.status === 'STREAMING' || playback.status === 'PLAYING';

  const isEmergency = isPlaying && (
    (playback.title || '').toLowerCase().includes('sirine') || 
    (playback.title || '').toLowerCase().includes('darurat') ||
    (playback.title || '').toLowerCase().includes('ews')
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* 1. TOP HEADER (COMPACT & CLEAN) */}
      <header className="bg-white border-b border-slate-200/90 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-15 flex items-center justify-between gap-4">
          {/* Logo & Online Quick Pill */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8.5 h-8.5 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
                <Radio className="w-4.5 h-4.5" />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-base font-semibold text-slate-900 leading-none">IntanWave</span>
                <span className="text-xs text-slate-500 font-normal hidden sm:inline">Audio Server</span>
              </div>
            </div>

            {/* Interactive Speaker Badge (Opens Full Monitoring Modal) */}
            <button
              onClick={() => setShowSpeakerMonitorModal(true)}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors cursor-pointer"
              title="Buka panel pemantauan speaker lengkap"
            >
              <span className={`w-2 h-2 rounded-full ${onlineCount > 0 ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
              <span>{onlineCount}/{speakers.length} Speaker Online</span>
            </button>

            {/* Active Browser Preview Indicator if running */}
            {isPreviewPlaying && (
              <div className="flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-sky-50 text-sky-700 border border-sky-200 animate-pulse">
                <Headphones className="w-3.5 h-3.5 text-sky-600" />
                <span>Pratinjau Web Aktif</span>
                <button 
                  onClick={handleStopBrowserPreview}
                  className="text-sky-800 hover:text-rose-600 font-bold ml-1"
                  title="Hentikan Pratinjau Web"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>

          {/* Right Tools */}
          <div className="flex items-center gap-2.5">
            {/* Live Clock */}
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 text-xs font-semibold">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>{currentTime}</span>
            </div>

            {/* Server Connection Indicator */}
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
              wsConnected 
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}>
              <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
              <span className="hidden sm:inline">{wsConnected ? 'Tersambung' : 'Terputus'}</span>
            </div>

            {/* Activity Logs Trigger */}
            <button 
              onClick={() => setShowLogsModal(true)}
              className="p-2 text-slate-600 hover:text-blue-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
              title="Riwayat Aktivitas"
            >
              <History className="w-4 h-4" />
            </button>

            {/* Network Settings Trigger */}
            <button 
              onClick={() => setShowSettings(true)}
              className="p-2 text-slate-600 hover:text-blue-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
              title="Pengaturan Jaringan"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* 2. ACTIVE BROADCAST BAR (STATUS + SOUNDBOARD MINI) */}
      <section className={`border-b transition-colors ${
        isEmergency
          ? 'bg-rose-700 text-white border-rose-800'
          : isPlaying 
            ? 'bg-blue-600 text-white border-blue-700' 
            : 'bg-slate-900 text-slate-100 border-slate-950'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-15 flex items-center justify-between gap-3">
          {/* Status Pill & Live Info */}
          <div className="flex items-center gap-2.5 min-w-0">
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold shrink-0 ${
              isEmergency
                ? 'bg-rose-800 text-white border border-rose-500'
                : isPlaying
                  ? 'bg-blue-700 text-white border border-blue-500'
                  : 'bg-slate-800 text-emerald-400 border border-slate-700'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                isEmergency 
                  ? 'bg-white animate-ping' 
                  : isPlaying 
                    ? 'bg-emerald-400 animate-pulse' 
                    : 'bg-emerald-400'
              }`} />
              {isEmergency ? 'Darurat' : isPlaying ? 'Berbunyi' : 'Siaga'}
            </span>

            <span className="text-slate-600 hidden md:inline">•</span>

            <h2 className="text-sm font-semibold text-white truncate max-w-xs sm:max-w-sm">
              {isPlaying ? playback.title : 'Server Siap Menyiarkan'}
            </h2>
          </div>

          {/* Soundboard Mini & Controls */}
          <div className="flex items-center gap-2 shrink-0">
            {isPlaying ? (
              <>
                <div className="flex items-center gap-2 mr-1">
                  <span className="text-xs font-medium text-blue-100 hidden sm:inline">
                    {formatSec(playback.elapsed)} / {formatSec(playback.duration)}
                  </span>
                  <div className="w-16 sm:w-28 bg-black/30 rounded-full h-1.5 overflow-hidden">
                    <div 
                      className="bg-emerald-400 h-full transition-all duration-300"
                      style={{ width: `${playback.duration ? Math.min(100, (playback.elapsed / playback.duration) * 100) : 0}%` }}
                    />
                  </div>
                </div>

                <button 
                  onClick={handleStop}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-all shadow-xs cursor-pointer"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Hentikan Siaran</span>
                </button>
              </>
            ) : (
              <>
                {/* SOUNDBOARD MINI TRIGGER: SIRINE DARURAT */}
                <button
                  onClick={() => setShowSirenConfirmModal(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-all shadow-xs cursor-pointer"
                  title="Siarkan sirine peringatan darurat ke speaker luar"
                >
                  <Siren className="w-3.5 h-3.5" />
                  <span>Sirine</span>
                </button>

                {/* SOUNDBOARD MINI TRIGGER: APEL PAGI */}
                <button
                  onClick={() => handlePlayFilenameToSpeakers('test_chime.wav')}
                  className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-all border border-slate-700 cursor-pointer"
                  title="Siarkan bel Apel Pagi ke speaker luar"
                >
                  <Bell className="w-3.5 h-3.5 text-blue-400" />
                  <span>Apel Pagi</span>
                </button>

                {/* SOUNDBOARD MINI TRIGGER: PENGINGAT K3 */}
                <button
                  onClick={() => handlePlayFilenameToSpeakers('safety_k3_chime.wav')}
                  className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-all border border-slate-700 cursor-pointer"
                  title="Siarkan pengingat K3 ke speaker luar"
                >
                  <HardHat className="w-3.5 h-3.5 text-emerald-400" />
                  <span>K3</span>
                </button>

                {/* TARGET SELECTOR DROPDOWN (LANGSUNG: SEMUA SPEAKER, ZONA 1, ZONA 2, DST) */}
                <CustomDropdown
                  value={currentTargetValue}
                  onChange={handleTargetChange}
                  options={targetOptions}
                  variant="dark"
                  size="sm"
                  buttonClassName="min-w-[155px]"
                />

                {/* DENGAR DI WEB (PREVIEW BROWSER) */}
                <button 
                  onClick={() => handleBrowserPreview('/api/audio/stream-file/test_chime.wav', 'global_bar')}
                  className={`flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-medium transition-all border cursor-pointer ${
                    previewingId === 'global_bar' && isPreviewPlaying
                      ? 'bg-sky-500/20 text-sky-300 border-sky-400'
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
                  }`}
                  title="Dengarkan jingle di browser saja (tanpa suara ke speaker fisik luar)"
                >
                  <Headphones className="w-3.5 h-3.5 text-sky-400" />
                  <span className="hidden lg:inline">{previewingId === 'global_bar' && isPreviewPlaying ? 'Hentikan' : 'Dengar Web'}</span>
                </button>
              </>
            )}
          </div>
        </div>
      </section>

      {/* 3. MAIN WORKSPACE (ALARM-FIRST CONSOLE) */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex-1 w-full space-y-4">
        
        {/* TAB NAVIGATION & PRIMARY ACTIONS */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Segmented Tab View */}
          <div className="flex items-center gap-1.5 p-1 bg-slate-200/70 rounded-xl">
            <button
              onClick={() => setActiveMainTab('schedules')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeMainTab === 'schedules'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              <span>Jadwal Siaran</span>
              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                activeMainTab === 'schedules' ? 'bg-blue-50 text-blue-700' : 'bg-slate-300/60 text-slate-700'
              }`}>
                {schedules.length}
              </span>
            </button>

            <button
              onClick={() => setActiveMainTab('audio')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeMainTab === 'audio'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Music className="w-3.5 h-3.5" />
              <span>Pustaka Berkas Audio</span>
              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                activeMainTab === 'audio' ? 'bg-blue-50 text-blue-700' : 'bg-slate-300/60 text-slate-700'
              }`}>
                {audioList.length}
              </span>
            </button>
          </div>

          {/* Primary Action Button */}
          <div className="flex items-center gap-2">
            {activeMainTab === 'schedules' ? (
              <button 
                onClick={handleOpenAddSchedule}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-all shadow-xs cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Tambah Jadwal</span>
              </button>
            ) : (
              <button 
                onClick={() => handleOpenUploadModal()}
                disabled={isUploading}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-all shadow-xs cursor-pointer disabled:opacity-50"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>{isUploading ? 'Mengunggah...' : 'Unggah Berkas'}</span>
              </button>
            )}
          </div>
        </div>

        {/* TAB 1: JADWAL SIARAN (ALARM-FIRST TABLE) */}
        {activeMainTab === 'schedules' && (
          <div className="space-y-3">
            {/* Ticker Next Alarm Card */}
            <div className="p-3 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-slate-600 min-w-0">
                <Clock className="w-4 h-4 text-blue-600 shrink-0" />
                <span className="font-semibold text-slate-700 shrink-0">Siaran berikutnya:</span>
                {nextSchedule ? (
                  <span className="truncate text-slate-900 font-semibold">
                    {nextSchedule.time_str} • {nextSchedule.name} ({nextSchedule.dayLabel})
                  </span>
                ) : (
                  <span className="text-slate-400">Tidak ada jadwal aktif</span>
                )}
              </div>
              {nextSchedule && (
                <span className="text-blue-700 bg-blue-50 border border-blue-200/80 px-2 py-0.5 rounded-full font-semibold shrink-0 text-[11px]">
                  {nextSchedule.countdown}
                </span>
              )}
            </div>

            {/* Alarm Table */}
            <div className="border border-slate-200/90 rounded-xl overflow-hidden bg-white shadow-2xs">
              {schedules.length === 0 ? (
                <div className="p-12 text-center space-y-3">
                  <Clock className="w-10 h-10 text-slate-300 mx-auto" />
                  <p className="text-xs font-medium text-slate-700">Belum ada jadwal tersimpan</p>
                  <button 
                    onClick={handleOpenAddSchedule}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-50 text-blue-600 hover:bg-blue-100 text-xs font-semibold transition-colors cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Buat jadwal pertama
                  </button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600">
                      <tr>
                        <th className="py-3 px-4 w-16 text-center">Aktif</th>
                        <th className="py-3 px-4 min-w-[130px]">Waktu Siar</th>
                        <th className="py-3 px-4">Nama Jadwal & Suara</th>
                        <th className="py-3 px-4 w-40">Pengulangan</th>
                        <th className="py-3 px-4 text-right pr-6 w-44">Aksi</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-xs">
                      {schedules.map((s) => {
                        const isPreviewThis = previewingId === `sched_${s.id}` && isPreviewPlaying;
                        return (
                          <tr 
                            key={s.id}
                            className={`hover:bg-slate-50/80 transition-colors ${
                              s.enabled ? 'bg-white' : 'bg-slate-50/40 text-slate-400'
                            }`}
                          >
                            {/* Toggle Switch */}
                            <td className="py-3 px-4 text-center whitespace-nowrap">
                              <button
                                onClick={() => handleToggleSchedule(s.id)}
                                className={`w-9 h-5 inline-flex items-center rounded-full p-0.5 cursor-pointer transition-colors ${
                                  s.enabled ? 'bg-emerald-500' : 'bg-slate-200'
                                }`}
                                title={s.enabled ? 'Klik untuk nonaktifkan' : 'Klik untuk aktifkan'}
                              >
                                <div
                                  className={`bg-white w-4 h-4 rounded-full shadow-xs transform transition-transform ${
                                    s.enabled ? 'translate-x-4' : 'translate-x-0'
                                  }`}
                                />
                              </button>
                            </td>

                            {/* Digital Clock / Multi-Times */}
                            <td className="py-3 px-4">
                              <div className="flex flex-wrap items-center gap-1.5 max-w-[220px]">
                                {parseScheduleTimes(s.time_str).map((t, idx) => (
                                  <span 
                                    key={idx}
                                    className={`px-2 py-0.5 rounded-md font-mono text-xs font-semibold tracking-tight border ${
                                      s.enabled 
                                        ? 'bg-blue-50/90 text-blue-700 border-blue-200/70 shadow-2xs' 
                                        : 'bg-slate-100 text-slate-400 border-slate-200/50'
                                    }`}
                                  >
                                    {t}
                                  </span>
                                ))}
                              </div>
                            </td>

                            {/* Nama Jadwal & Audio & Target */}
                            <td className="py-3 px-4 min-w-0">
                              <div className={`font-semibold text-sm leading-snug truncate ${
                                s.enabled ? 'text-slate-900' : 'text-slate-500'
                              }`}>
                                {s.name}
                              </div>
                              <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-1 truncate">
                                <div className="flex items-center gap-1 truncate">
                                  <Music className="w-3 h-3 text-blue-500 shrink-0" />
                                  <span className="truncate">{s.audio_title || 'Audio default'}</span>
                                </div>
                                <span className="text-slate-300">•</span>
                                <span className="inline-flex items-center text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200/60 shrink-0">
                                  {(s.target_mode === 'group' || s.target_mode === 'zone') && (s.target_group || s.target_zone)
                                    ? `Group: ${s.target_group || s.target_zone}`
                                    : s.target_mode === 'speaker' && s.target_speaker_id
                                    ? `Speaker: ${speakers.find(sp => sp.id === s.target_speaker_id)?.name || `ID ${s.target_speaker_id}`}`
                                    : 'Semua Speaker'}
                                </span>
                              </div>
                            </td>

                            {/* Pengulangan */}
                            <td className="py-3 px-4 whitespace-nowrap">
                              <span className="inline-block px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200/60">
                                {getScheduleLabel(s)}
                              </span>
                            </td>

                            {/* Aksi Cepat */}
                            <td className="py-3 px-4 text-right pr-6 whitespace-nowrap">
                              <div className="inline-flex items-center gap-1 justify-end">
                                {/* Dengar di Web */}
                                <button
                                  onClick={() => handleBrowserPreview(`/api/audio/${s.audio_file_id}/stream`, `sched_${s.id}`)}
                                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                                    isPreviewThis
                                      ? 'bg-sky-100 text-sky-700'
                                      : 'text-slate-400 hover:text-sky-600 hover:bg-sky-50'
                                  }`}
                                  title="Dengarkan di browser saja"
                                >
                                  <Headphones className="w-3.5 h-3.5" />
                                </button>

                                {/* Putar ke Speaker Luar */}
                                <button 
                                  onClick={() => handlePlayToSpeakers(s.audio_file_id)}
                                  title="Siarkan langsung ke speaker fisik luar"
                                  className="p-1.5 text-slate-400 hover:text-blue-600 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                                >
                                  <Play className="w-3.5 h-3.5 fill-current" />
                                </button>

                                {/* Salin */}
                                <button 
                                  onClick={() => handleDuplicateSchedule(s)}
                                  title="Salin jadwal ini"
                                  className="p-1.5 text-slate-400 hover:text-blue-600 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                                >
                                  <Copy className="w-3.5 h-3.5" />
                                </button>

                                {/* Edit */}
                                <button 
                                  onClick={() => handleOpenEditSchedule(s)}
                                  title="Edit jadwal ini"
                                  className="p-1.5 text-slate-400 hover:text-blue-600 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                                >
                                  <Settings className="w-3.5 h-3.5" />
                                </button>

                                {/* Hapus */}
                                <button 
                                  onClick={() => handleDeleteSchedule(s.id)}
                                  title="Hapus jadwal"
                                  className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: PUSTAKA BERKAS AUDIO */}
        {activeMainTab === 'audio' && (
          <div className="space-y-3">
            {/* Filter Pills Bar */}
            <div className="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-wrap items-center justify-between gap-2.5 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400 font-medium mr-1 text-[11px]">Kategori:</span>
                <button
                  type="button"
                  onClick={() => setAudioCategoryFilter('all')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    audioCategoryFilter === 'all'
                      ? 'bg-blue-600 text-white shadow-2xs'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  Semua ({audioList.length})
                </button>
                <button
                  type="button"
                  onClick={() => setAudioCategoryFilter('biasa')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    audioCategoryFilter === 'biasa'
                      ? 'bg-blue-600 text-white shadow-2xs'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  <Volume2 className="w-3 h-3" />
                  <span>Suara Biasa ({audioList.filter(a => (a.category || 'biasa') === 'biasa').length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setAudioCategoryFilter('darurat')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    audioCategoryFilter === 'darurat'
                      ? 'bg-rose-600 text-white shadow-2xs'
                      : 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200/80'
                  }`}
                >
                  <Siren className="w-3 h-3 text-rose-500 animate-pulse" />
                  <span>Suara Darurat ({emergencyAudios.length})</span>
                </button>
              </div>

              <div className="text-[11px] text-slate-400">
                Gunakan tombol pensil di kolom aksi jika ingin mengubah kondisi atau nama audio.
              </div>
            </div>

            {/* Table Container */}
            <div className="border border-slate-200/90 rounded-xl overflow-hidden bg-white shadow-2xs">
              {filteredAudioList.length === 0 ? (
                <div className="p-12 text-center space-y-3">
                  <Music className="w-10 h-10 text-slate-300 mx-auto" />
                  <p className="text-xs font-medium text-slate-700">
                    {audioList.length === 0 
                      ? 'Belum ada berkas audio tersimpan' 
                      : 'Tidak ada berkas audio untuk kategori ini'}
                  </p>
                  <button 
                    onClick={() => handleOpenUploadModal()}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-50 text-blue-600 hover:bg-blue-100 text-xs font-semibold transition-colors cursor-pointer"
                  >
                    <Upload className="w-3.5 h-3.5" /> Unggah berkas audio
                  </button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600">
                      <tr>
                        <th className="py-3 px-4 w-16">Format</th>
                        <th className="py-3 px-4 w-32">Kondisi / Tipe</th>
                        <th className="py-3 px-4">Nama Berkas</th>
                        <th className="py-3 px-4 w-28">Durasi</th>
                        <th className="py-3 px-4 w-28">Ukuran</th>
                        <th className="py-3 px-4 text-right pr-6 w-36">Aksi</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-xs">
                      {filteredAudioList.map((a) => {
                        const isPreviewThis = previewingId === `lib_${a.id}` && isPreviewPlaying;
                        const isDarurat = (a.category || 'biasa') === 'darurat';
                        return (
                          <tr 
                            key={a.id} 
                            className={`transition-colors ${
                              isDarurat ? 'bg-rose-50/25 hover:bg-rose-50/50' : 'hover:bg-slate-50/80'
                            }`}
                          >
                            <td className="py-3 px-4 whitespace-nowrap">
                              <span className={`w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-semibold ${
                                isDarurat ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-700'
                              }`}>
                                {a.format}
                              </span>
                            </td>

                            {/* Kondisi / Tipe (Label Visual Statis) */}
                            <td className="py-3 px-4 whitespace-nowrap">
                              {isDarurat ? (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-rose-100/80 text-rose-700 border border-rose-200 shadow-2xs">
                                  <Siren className="w-3.5 h-3.5 text-rose-600 animate-pulse" />
                                  <span>Darurat</span>
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                                  <Volume2 className="w-3.5 h-3.5 text-slate-400" />
                                  <span>Biasa</span>
                                </span>
                              )}
                            </td>

                            <td className="py-3 px-4 min-w-0">
                              <div className={`font-semibold truncate flex items-center gap-1.5 ${
                                isDarurat ? 'text-rose-950 font-bold' : 'text-slate-900'
                              }`}>
                                {isDarurat && <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />}
                                <span className="truncate">{a.display_name}</span>
                              </div>
                              <div className="text-[10px] text-slate-400 truncate mt-0.5">{a.filename}</div>
                            </td>

                            <td className="py-3 px-4 whitespace-nowrap text-slate-600 font-medium">
                              {formatSec(a.duration)}
                            </td>
                            <td className="py-3 px-4 whitespace-nowrap text-slate-600 font-medium">
                              {Math.round(a.size / 1024)} KB
                            </td>
                            <td className="py-3 px-4 text-right pr-6 whitespace-nowrap">
                              <div className="inline-flex items-center gap-1 justify-end">
                                {/* Dengar di Web */}
                                <button 
                                  onClick={() => handleBrowserPreview(`/api/audio/${a.id}/stream`, `lib_${a.id}`)}
                                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                                    isPreviewThis
                                      ? 'bg-sky-100 text-sky-700'
                                      : 'text-slate-400 hover:text-sky-600 hover:bg-sky-50'
                                  }`}
                                  title="Dengarkan di browser saja"
                                >
                                  <Headphones className="w-3.5 h-3.5" />
                                </button>

                                {/* Putar ke Speaker Luar */}
                                <button 
                                  onClick={() => handlePlayToSpeakers(a.id)}
                                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                                    isDarurat 
                                      ? 'text-rose-600 hover:bg-rose-100/70 hover:text-rose-700' 
                                      : 'text-slate-400 hover:text-blue-600 hover:bg-slate-100'
                                  }`}
                                  title="Siarkan ke speaker fisik luar"
                                >
                                  <Play className="w-3.5 h-3.5 fill-current" />
                                </button>

                                {/* Ubah Kondisi / Edit */}
                                <button 
                                  onClick={() => handleRequestChangeCategory(a, a.category || 'biasa')}
                                  className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors cursor-pointer"
                                  title="Ubah kondisi atau nama audio"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>

                                {/* Hapus */}
                                <button 
                                  onClick={() => handleDeleteAudio(a.id)}
                                  className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                                  title="Hapus berkas"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFilePickedForUpload} 
                accept=".mp3,.wav,.ogg,.flac" 
                className="hidden" 
              />
            </div>
          </div>
        )}

      </main>

      {/* ========================================================= */}
      {/* MODAL: MONITORING & MANAJEMEN SPEAKER                     */}
      {/* ========================================================= */}
      {showSpeakerMonitorModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-4xl max-h-[88vh] flex flex-col p-5 shadow-xl">
            {/* Header Modal */}
            <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <Volume2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-slate-900">Monitoring & Status Speaker</h3>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      {onlineCount}/{speakers.length} Online
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">Pantau status jaringan, latensi ping, dan uji tembak audio horn di lapangan</p>
                </div>
              </div>
              <button 
                onClick={() => setShowSpeakerMonitorModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Filter Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-2.5 py-3 border-b border-slate-100 text-xs">
              <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[260px]">
                {/* Search */}
                <div className="relative flex-1 min-w-[160px] max-w-xs">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Cari nama, IP, group..."
                    className="w-full pl-8 pr-2.5 py-1.5 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden bg-slate-50/50"
                  />
                  {searchQuery && (
                    <button 
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>

                {/* Status Dropdown */}
                <CustomDropdown
                  value={statusFilter}
                  onChange={setStatusFilter}
                  options={[
                    { value: 'all', label: 'Semua Status' },
                    { value: 'online', label: 'Online' },
                    { value: 'offline', label: 'Offline' }
                  ]}
                  variant="light"
                  size="sm"
                />

                {/* Group Dropdown */}
                <CustomDropdown
                  value={groupFilter}
                  onChange={setGroupFilter}
                  options={[
                    { value: 'all', label: 'Semua Group' },
                    ...groupsList.map((g) => ({
                      value: g,
                      label: `Group: ${g}`
                    }))
                  ]}
                  variant="light"
                  size="sm"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowGroupModal(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-all cursor-pointer"
                  title="Tambah, ubah nama, atau kelola group speaker"
                >
                  <Layers className="w-3.5 h-3.5 text-slate-600" />
                  <span>Kelola Group</span>
                </button>

                <button
                  onClick={handleScanAll}
                  disabled={isScanning}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-all disabled:opacity-50 cursor-pointer"
                  title="Pindai status ping seluruh speaker"
                >
                  <RefreshCw className={`w-3.5 h-3.5 text-slate-600 ${isScanning ? 'animate-spin' : ''}`} />
                  <span>{isScanning ? 'Memindai...' : 'Scan Ping'}</span>
                </button>

                <button
                  onClick={handleOpenAddSpeaker}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-all shadow-xs cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Tambah Speaker</span>
                </button>
              </div>
            </div>

            {/* Table in Scrollable Container */}
            <div className="flex-1 overflow-y-auto min-h-0 my-2 border border-slate-200/90 rounded-xl">
              {filteredSpeakers.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400">
                  Tidak ada speaker yang sesuai filter pencarian.
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600 z-10">
                    <tr>
                      <th className="py-2.5 px-3.5">Status</th>
                      <th className="py-2.5 px-3">Nama Perangkat</th>
                      <th className="py-2.5 px-3">Group</th>
                      <th className="py-2.5 px-3">Alamat IP</th>
                      <th className="py-2.5 px-3 text-right pr-4">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {filteredSpeakers.map((s) => {
                      const isOnline = s.status === 'online';
                      const isTestingThis = testingSpeakerId === s.id;
                      const isPingingThis = pingingSpeakerId === s.id;
                      const isCopied = copiedSpeakerId === s.id;

                      return (
                        <tr key={s.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-2 px-3.5 whitespace-nowrap">
                            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border ${
                              isOnline 
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                                : 'bg-rose-50 text-rose-700 border-rose-200'
                            }`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${
                                isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
                              }`} />
                              <span>{isOnline ? (s.device_type === 'node' ? 'Online (DHCP)' : `${s.latency_ms || 1}ms`) : 'Offline'}</span>
                            </span>
                          </td>
                          <td className="py-2 px-3 font-semibold text-slate-900 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              {s.device_type === 'node' ? (
                                <span className="p-1 rounded bg-indigo-50 text-indigo-600 shrink-0" title="PC Audio Node (Windows DHCP)">
                                  <Laptop className="w-3.5 h-3.5" />
                                </span>
                              ) : (
                                <span className="p-1 rounded bg-slate-100 text-slate-500 shrink-0" title="IP Horn Speaker Fisik">
                                  <Volume2 className="w-3.5 h-3.5" />
                                </span>
                              )}
                              <div className="min-w-0">
                                <span className="block truncate">{s.name}</span>
                                {s.hostname && (
                                  <span className="block text-[10px] text-slate-400 font-normal truncate">{s.hostname}</span>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="py-2 px-3">
                            <div className="flex flex-wrap items-center gap-1">
                              {getSpeakerGroups(s).map(g => (
                                <span key={g} className="inline-block px-2 py-0.5 rounded-md text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/70">
                                  {g}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-2 px-3 whitespace-nowrap">
                            <div className="inline-flex items-center gap-1 text-slate-600 bg-slate-50 px-2 py-0.5 rounded-md border border-slate-100 text-[11px]">
                              <span>
                                {s.ip_address?.startsWith('pending-') 
                                  ? 'Menunggu DHCP...' 
                                  : `${s.ip_address}:${s.port || 5004}`}
                              </span>
                              {!s.ip_address?.startsWith('pending-') && (
                                <button
                                  onClick={() => handleCopyIp(s.id, s.ip_address)}
                                  className="text-slate-400 hover:text-blue-600 p-0.5 transition-colors cursor-pointer"
                                  title="Salin IP"
                                >
                                  {isCopied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                                </button>
                              )}
                            </div>
                          </td>
                          <td className="py-2 px-3 text-right pr-4 whitespace-nowrap">
                            <div className="inline-flex items-center gap-1 justify-end">
                              <button
                                onClick={() => handleTestPhysicalSpeaker(s)}
                                disabled={isTestingThis}
                                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all cursor-pointer ${
                                  isTestingThis 
                                    ? 'bg-blue-100 text-blue-700 animate-pulse' 
                                    : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                                }`}
                                title="Kirim suara tes ke speaker fisik ini"
                              >
                                <Radio className="w-3 h-3" />
                                <span>{isTestingThis ? 'Memutar...' : 'Tes Fisik'}</span>
                              </button>

                              <button
                                onClick={() => handlePingSpeaker(s)}
                                disabled={isPingingThis}
                                className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors cursor-pointer"
                                title="Cek ping speaker ini"
                              >
                                <RefreshCw className={`w-3.5 h-3.5 ${isPingingThis ? 'animate-spin text-blue-600' : ''}`} />
                              </button>

                              <button
                                onClick={() => handleOpenEditSpeaker(s)}
                                className="p-1 text-slate-400 hover:text-blue-600 hover:bg-slate-100 rounded transition-colors cursor-pointer"
                                title="Edit speaker"
                              >
                                <Settings className="w-3.5 h-3.5" />
                              </button>

                              <button
                                onClick={() => handleDeleteSpeaker(s.id, s.name)}
                                className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors cursor-pointer"
                                title="Hapus speaker"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {/* Modal Footer */}
            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setShowSpeakerMonitorModal(false)}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors cursor-pointer"
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: TAMBAH / EDIT SPEAKER                               */}
      {/* ========================================================= */}
      {showSpeakerModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-md p-5 shadow-xl">
            <div className="flex items-center justify-between mb-3.5">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  {editingSpeaker ? 'Edit Konfigurasi Speaker' : 'Tambah Speaker Baru'}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">Pengaturan perangkat IP Horn atau Node Client</p>
              </div>
              <button onClick={() => setShowSpeakerModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4.5 h-4.5" />
              </button>
            </div>

            <form onSubmit={handleSaveSpeaker} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Nama Speaker</label>
                <input 
                  type="text" 
                  required
                  placeholder="Contoh: Dermaga 7 / Pos Keamanan"
                  value={speakerForm.name}
                  onChange={e => setSpeakerForm({ ...speakerForm, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                />
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-700 mb-1">Alamat IP</label>
                  <input 
                    type="text" 
                    required
                    placeholder="192.168.1.100"
                    value={speakerForm.ip_address}
                    onChange={e => setSpeakerForm({ ...speakerForm, ip_address: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Port RTP</label>
                  <input 
                    type="number" 
                    required
                    value={speakerForm.port}
                    onChange={e => setSpeakerForm({ ...speakerForm, port: parseInt(e.target.value) || 5004 })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-slate-700">Group Audio</label>
                  <span className="text-[11px] text-slate-400">Pilih 1 atau lebih group (klik badge)</span>
                </div>
                <input 
                  type="text" 
                  required
                  placeholder="Ketik nama group (pisahkan koma jika > 1, misal: Kantor, Satpam)"
                  value={speakerForm.groupsText || ''}
                  onChange={e => setSpeakerForm({ ...speakerForm, groupsText: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                />
                {groupsList.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 mt-2">
                    {groupsList.map(g => {
                      const selected = (speakerForm.groupsText || '')
                        .split(',')
                        .map(x => x.trim().toLowerCase())
                        .includes(g.toLowerCase());
                      return (
                        <button
                          type="button"
                          key={g}
                          onClick={() => toggleSpeakerFormGroup(g)}
                          className={`px-2.5 py-1 rounded-lg text-[11px] border transition-all cursor-pointer ${
                            selected
                              ? 'bg-blue-600 border-blue-600 text-white font-medium shadow-2xs'
                              : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                          }`}
                        >
                          {g} {selected && '✓'}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Uji Ping Sebelum Simpan */}
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-slate-500" />
                  <span className="text-slate-600 font-medium">Tes IP:</span>
                  {modalPingStatus.result && (
                    <span className={`font-semibold ${
                      modalPingStatus.result.online ? 'text-emerald-600' : 'text-rose-600'
                    }`}>
                      {modalPingStatus.result.online 
                        ? `Online (${modalPingStatus.result.latency}ms)` 
                        : 'Offline'}
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleTestModalPing}
                  disabled={modalPingStatus.testing || !speakerForm.ip_address}
                  className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-medium text-xs transition-colors disabled:opacity-50"
                >
                  {modalPingStatus.testing ? 'Menguji...' : 'Uji Ping'}
                </button>
              </div>

              <div className="pt-1.5 flex justify-end gap-2">
                <button 
                  type="button" 
                  onClick={() => setShowSpeakerModal(false)}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100"
                >
                  Batal
                </button>
                <button 
                  type="submit" 
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
                >
                  {editingSpeaker ? 'Simpan' : 'Tambahkan'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: KONFIRMASI SIARAN SIRINE DARURAT                    */}
      {/* ========================================================= */}
      {showSirenConfirmModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-md p-5 shadow-xl">
            <div className="flex items-start gap-3.5">
              <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 shrink-0">
                <Siren className="w-6 h-6 text-rose-600 animate-pulse" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-slate-900 leading-snug">
                  Konfirmasi Siaran Sirine Darurat
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Sirine peringatan darurat (EWS) akan langsung dibunyikan ke speaker fisik luar. Pastikan kondisi darurat atau telah dikoordinasikan.
                </p>
              </div>
              <button 
                onClick={() => setShowSirenConfirmModal(false)} 
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4 p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-medium">Target Siaran:</span>
                <span className="font-semibold text-slate-800 truncate max-w-[220px]">{targetSummaryText}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-500 font-medium shrink-0">Berkas Suara:</span>
                {emergencyAudios.length > 1 ? (
                  <select
                    value={selectedEmergencyAudio || emergencyAudios[0]?.filename || 'sirine_ews_test.wav'}
                    onChange={e => setSelectedEmergencyAudio(e.target.value)}
                    className="px-2 py-1 rounded-lg border border-rose-300 bg-white text-xs text-rose-700 font-semibold outline-hidden"
                  >
                    {emergencyAudios.map(ea => (
                      <option key={ea.id} value={ea.filename}>
                        {ea.display_name} ({ea.filename})
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="font-semibold text-rose-600">
                    {emergencyAudios[0]?.display_name || 'sirine_ews_test.wav'}
                  </span>
                )}
              </div>
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowSirenConfirmModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowSirenConfirmModal(false);
                  const chosenAudio = selectedEmergencyAudio || emergencyAudios[0]?.filename || 'sirine_ews_test.wav';
                  handlePlayFilenameToSpeakers(chosenAudio);
                }}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-xs transition-all cursor-pointer"
              >
                <Siren className="w-3.5 h-3.5" />
                <span>Ya, Bunyikan Sirine</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: TAMBAH / SALIN JADWAL                               */}
      {/* ========================================================= */}
      {showAddSchedule && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-md p-5 shadow-xl">
            <div className="flex items-center justify-between mb-3.5">
              <h3 className="text-base font-semibold text-slate-900">{editingScheduleId ? 'Edit Jadwal Siaran' : 'Tambah Jadwal Siaran'}</h3>
              <button onClick={() => setShowAddSchedule(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4.5 h-4.5" />
              </button>
            </div>

            <form onSubmit={handleSaveSchedule} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Nama Jadwal</label>
                <input 
                  type="text" 
                  required
                  placeholder="Contoh: Apel Pagi"
                  value={newSchedule.name}
                  onChange={e => setNewSchedule({ ...newSchedule, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Berkas Audio</label>
                <CustomDropdown
                  value={newSchedule.audio_file_id}
                  onChange={val => setNewSchedule({ ...newSchedule, audio_file_id: parseInt(val) })}
                  options={audioList.map(a => ({
                    value: a.id,
                    label: a.category === 'darurat' ? `🔴 [Darurat] ${a.display_name}` : a.display_name,
                    sublabel: `${a.category === 'darurat' ? 'Suara Darurat (EWS)' : 'Suara Biasa'} • ${a.filename} • ${formatSec(a.duration)}`
                  }))}
                  variant="light"
                  className="w-full"
                  buttonClassName="w-full bg-white justify-between"
                  placeholder="Pilih berkas audio..."
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Target Siaran</label>
                <CustomDropdown
                  value={
                    (newSchedule.target_mode === 'group' || newSchedule.target_mode === 'zone') && (newSchedule.target_group || newSchedule.target_zone)
                      ? `group:${newSchedule.target_group || newSchedule.target_zone}`
                      : newSchedule.target_mode === 'speaker' && newSchedule.target_speaker_id
                      ? `speaker:${newSchedule.target_speaker_id}`
                      : 'all'
                  }
                  onChange={(val) => {
                    if (val === 'all') {
                      setNewSchedule(prev => ({ ...prev, target_mode: 'all', target_group: '', target_zone: '', target_speaker_id: 0 }));
                    } else if (val.startsWith('group:') || val.startsWith('zone:')) {
                      const gName = val.replace(/^(group:|zone:)/, '');
                      setNewSchedule(prev => ({ ...prev, target_mode: 'group', target_group: gName, target_zone: gName, target_speaker_id: 0 }));
                    } else if (val.startsWith('speaker:')) {
                      setNewSchedule(prev => ({ ...prev, target_mode: 'speaker', target_group: '', target_zone: '', target_speaker_id: parseInt(val.replace('speaker:', ''), 10) }));
                    }
                  }}
                  options={targetOptions}
                  variant="light"
                  className="w-full"
                  buttonClassName="w-full bg-white justify-between"
                  placeholder="Pilih target siaran..."
                />
              </div>

              {/* Multi-Time Picker */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-blue-600" />
                    <span>Waktu Siar (Bisa Banyak Jam)</span>
                  </label>
                  <span className="text-[11px] font-medium text-slate-400">
                    {parseScheduleTimes(newSchedule.time_str).length} jam dipilih
                  </span>
                </div>

                {/* List of active time badges */}
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 mb-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {parseScheduleTimes(newSchedule.time_str).map((t, idx) => (
                      <span 
                        key={idx}
                        className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-lg bg-white border border-blue-200/80 text-blue-700 font-mono text-xs font-semibold shadow-2xs"
                      >
                        <span>{t}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveTime(t)}
                          className="p-0.5 rounded-md hover:bg-red-50 hover:text-red-600 text-slate-400 cursor-pointer transition-colors"
                          title="Hapus jam ini"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                    {parseScheduleTimes(newSchedule.time_str).length === 0 && (
                      <span className="text-xs text-amber-600 italic">Pilih minimal 1 jam siaran</span>
                    )}
                  </div>
                </div>

                {/* Input tambah jam & preset */}
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <div className="flex items-center gap-1.5">
                    <input 
                      type="time" 
                      value={scheduleTimeInput}
                      onChange={e => setScheduleTimeInput(e.target.value)}
                      className="px-2.5 py-1.5 rounded-xl border border-slate-200 text-xs font-medium focus:ring-2 focus:ring-blue-500 outline-hidden bg-white"
                    />
                    <button
                      type="button"
                      onClick={handleAddTime}
                      className="px-2.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium cursor-pointer transition-colors flex items-center gap-1 shadow-2xs"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Tambah Jam</span>
                    </button>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-slate-500 sm:ml-auto">
                    <span className="text-slate-400">Preset:</span>
                    <button 
                      type="button" 
                      onClick={() => handleAddPresetTime('08:00')} 
                      className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-600 cursor-pointer transition-colors"
                    >
                      08:00
                    </button>
                    <button 
                      type="button" 
                      onClick={() => handleAddPresetTime('11:45')} 
                      className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-600 cursor-pointer transition-colors"
                    >
                      11:45
                    </button>
                    <button 
                      type="button" 
                      onClick={() => handleAddPresetTime('15:00')} 
                      className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-600 cursor-pointer transition-colors"
                    >
                      15:00
                    </button>
                    <button 
                      type="button" 
                      onClick={() => handleAddPresetTime('17:00')} 
                      className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-600 cursor-pointer transition-colors"
                    >
                      17:00
                    </button>
                  </div>
                </div>
              </div>

              {/* Pengulangan */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Pengulangan Hari</label>
                <CustomDropdown
                  value={newSchedule.schedule_type}
                  onChange={val => {
                    if (val === 'daily') setSchedulePreset('daily');
                    else if (val === 'weekdays') setSchedulePreset('weekdays');
                    else setNewSchedule({ ...newSchedule, schedule_type: val });
                  }}
                  options={[
                    { value: 'daily', label: 'Setiap hari (Sen - Min)' },
                    { value: 'weekdays', label: 'Senin sampai Jumat' },
                    { value: 'custom', label: 'Pilih hari tertentu' },
                    { value: 'once', label: 'Sekali jalan' }
                  ]}
                  variant="light"
                  className="w-full"
                  buttonClassName="w-full bg-white justify-between"
                />
              </div>

              {/* Day Selection Pills */}
              {newSchedule.schedule_type !== 'once' && (
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="block text-[11px] font-semibold text-slate-700">Pilih Hari Aktif:</label>
                    <div className="flex items-center gap-1.5 text-[11px]">
                      <button 
                        type="button" 
                        onClick={() => setSchedulePreset('daily')}
                        className={`hover:underline cursor-pointer ${newSchedule.schedule_type === 'daily' ? 'font-bold text-blue-600' : 'text-slate-500'}`}
                      >
                        Semua
                      </button>
                      <span className="text-slate-300">•</span>
                      <button 
                        type="button" 
                        onClick={() => setSchedulePreset('weekdays')}
                        className={`hover:underline cursor-pointer ${newSchedule.schedule_type === 'weekdays' ? 'font-bold text-blue-600' : 'text-slate-500'}`}
                      >
                        Sen-Jum
                      </button>
                      <span className="text-slate-300">•</span>
                      <button 
                        type="button" 
                        onClick={() => setSchedulePreset('weekends')}
                        className={`hover:underline cursor-pointer ${newSchedule.days_of_week === 'sat,sun' ? 'font-bold text-blue-600' : 'text-slate-500'}`}
                      >
                        Sab-Min
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-7 gap-1">
                    {DAYS_CONFIG.map(day => {
                      const isSelected = (newSchedule.days_of_week || '')
                        .split(',')
                        .map(d => d.trim().toLowerCase())
                        .includes(day.key);
                      return (
                        <button
                          key={day.key}
                          type="button"
                          onClick={() => toggleScheduleDay(day.key)}
                          className={`py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer border ${
                            isSelected
                              ? 'bg-blue-600 border-blue-600 text-white shadow-2xs'
                              : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-100'
                          }`}
                          title={day.full}
                        >
                          {day.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="pt-1.5 flex justify-end gap-2">
                <button 
                  type="button" 
                  onClick={() => setShowAddSchedule(false)}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100"
                >
                  Batal
                </button>
                <button 
                  type="submit" 
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
                >
                  Simpan Jadwal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: RIWAYAT AKTIVITAS (AUDIT LOGS)                      */}
      {/* ========================================================= */}
      {showLogsModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-2xl max-h-[85vh] flex flex-col p-5 shadow-xl">
            <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
              <div>
                <h3 className="text-base font-semibold text-slate-900">Riwayat Aktivitas</h3>
                <p className="text-xs text-slate-500">Catatan audit kejadian sistem siaran</p>
              </div>
              <button onClick={() => setShowLogsModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4.5 h-4.5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 mt-3 text-xs pr-1">
              {logs.map((log) => (
                <div key={log.id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex items-start gap-2">
                  <span className="text-slate-400 shrink-0 text-[11px]">{log.timestamp}</span>
                  <span className="text-slate-800 font-medium">{log.event}:</span>
                  <span className="text-slate-600">{log.details}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: KONFIRMASI UBAH KONDISI / KATEGORI SUARA           */}
      {/* ========================================================= */}
      {categoryChangeTarget && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-md p-5 shadow-xl">
            {/* Header */}
            <div className="flex items-start gap-3.5">
              <div className={`p-2.5 rounded-xl border shrink-0 ${
                categoryChangeTarget.targetCategory === 'darurat'
                  ? 'bg-rose-50 border-rose-200 text-rose-600'
                  : 'bg-blue-50 border-blue-200 text-blue-600'
              }`}>
                {categoryChangeTarget.targetCategory === 'darurat' ? (
                  <Siren className="w-6 h-6 animate-pulse" />
                ) : (
                  <Volume2 className="w-6 h-6" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-slate-900 leading-snug">
                  {categoryChangeTarget.targetCategory === 'darurat'
                    ? 'Ubah ke Suara Darurat (EWS)?'
                    : 'Ubah ke Suara Biasa?'}
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  {categoryChangeTarget.targetCategory === 'darurat'
                    ? 'Suara ini akan ditandai merah dan dialokasikan untuk sirine bahaya atau evakuasi darurat.'
                    : 'Suara ini akan dikembalikan menjadi suara operasional standar reguler.'}
                </p>
              </div>
              <button 
                onClick={() => setCategoryChangeTarget(null)} 
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content & Details */}
            <div className="mt-4 p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-1">Nama Tampilan Audio:</label>
                <input
                  type="text"
                  value={editingDisplayName}
                  onChange={e => setEditingDisplayName(e.target.value)}
                  placeholder="Ketik nama tampilan audio..."
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-900 focus:ring-2 focus:ring-blue-500 outline-hidden font-medium"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-1.5">Pilih Kondisi Suara:</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setCategoryChangeTarget(prev => ({ ...prev, targetCategory: 'biasa' }))}
                    className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                      categoryChangeTarget.targetCategory === 'biasa'
                        ? 'bg-blue-50/80 border-blue-500 text-blue-900 shadow-2xs font-semibold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 text-xs font-semibold">
                      <Volume2 className="w-3.5 h-3.5 text-blue-600" />
                      <span>Suara Biasa</span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">Operasional reguler</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setCategoryChangeTarget(prev => ({ ...prev, targetCategory: 'darurat' }))}
                    className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                      categoryChangeTarget.targetCategory === 'darurat'
                        ? 'bg-rose-50 border-rose-500 text-rose-900 shadow-2xs font-semibold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-600">
                      <Siren className="w-3.5 h-3.5 animate-pulse" />
                      <span>Suara Darurat</span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">Sirine & alarm EWS</div>
                  </button>
                </div>
              </div>

              <div className="pt-1 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
                <span>Nama berkas fisik:</span>
                <span className="font-mono text-slate-700">{categoryChangeTarget.audio.filename}</span>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setCategoryChangeTarget(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleConfirmCategoryChange}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white shadow-xs transition-all cursor-pointer ${
                  categoryChangeTarget.targetCategory === 'darurat'
                    ? 'bg-rose-600 hover:bg-rose-700'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                <Check className="w-3.5 h-3.5" />
                <span>Simpan & Ubah</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: UNGGAH BERKAS AUDIO (BIASA ATAU DARURAT)           */}
      {/* ========================================================= */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-lg flex flex-col p-5 shadow-xl">
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                  <Upload className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900">Unggah Berkas Audio</h3>
                  <p className="text-xs text-slate-500">Pilih kondisi suara (Biasa atau Darurat) saat menyimpan</p>
                </div>
              </div>
              <button 
                onClick={() => {
                  setShowUploadModal(false);
                  setUploadSelectedFile(null);
                }} 
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-4.5 h-4.5" />
              </button>
            </div>

            <form onSubmit={handleSubmitUpload} className="mt-4 space-y-4">
              {/* File Selector Dropzone */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Berkas Audio</label>
                {uploadSelectedFile ? (
                  <div className="p-3 rounded-xl border border-blue-200 bg-blue-50/40 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs uppercase shrink-0">
                        {uploadSelectedFile.name.split('.').pop() || 'AUD'}
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-slate-900 truncate">
                          {uploadSelectedFile.name}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {Math.round(uploadSelectedFile.size / 1024)} KB
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        if (fileInputRef.current) fileInputRef.current.click();
                      }}
                      className="px-2.5 py-1 text-xs font-medium text-blue-600 hover:bg-blue-100/60 rounded-lg cursor-pointer transition-colors"
                    >
                      Ganti Berkas
                    </button>
                  </div>
                ) : (
                  <div 
                    onClick={() => fileInputRef.current && fileInputRef.current.click()}
                    className="border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-xl p-5 text-center cursor-pointer transition-colors bg-slate-50/50 hover:bg-blue-50/30"
                  >
                    <Upload className="w-7 h-7 text-slate-400 mx-auto mb-1.5" />
                    <p className="text-xs font-semibold text-slate-700">Klik untuk memilih berkas suara</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">Mendukung format MP3, WAV, OGG, FLAC</p>
                  </div>
                )}
              </div>

              {/* Nama Tampilan */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Nama Tampilan Audio
                </label>
                <input 
                  type="text" 
                  required
                  placeholder="Contoh: Apel Pagi, Sirine Darurat Gempa, Bel K3..."
                  value={uploadDisplayName}
                  onChange={e => setUploadDisplayName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                />
              </div>

              {/* Pilihan Kondisi / Kategori Suara */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-slate-700">
                    Kondisi / Tipe Suara:
                  </label>
                  <span className="text-[11px] text-slate-400">Pilih salah satu kondisi</span>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  {/* Opsi 1: Suara Biasa */}
                  <div
                    onClick={() => setUploadCategory('biasa')}
                    className={`p-3 rounded-xl border-2 cursor-pointer transition-all ${
                      uploadCategory === 'biasa'
                        ? 'border-blue-500 bg-blue-50/50 shadow-2xs'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5 font-semibold text-xs text-slate-900">
                        <Volume2 className="w-4 h-4 text-blue-600" />
                        <span>Suara Biasa</span>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                        Biasa
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 leading-tight">
                      Pengumuman umum, bel operasional, apel pagi, atau pengingat K3.
                    </p>
                  </div>

                  {/* Opsi 2: Suara Darurat (Merah) */}
                  <div
                    onClick={() => setUploadCategory('darurat')}
                    className={`p-3 rounded-xl border-2 cursor-pointer transition-all ${
                      uploadCategory === 'darurat'
                        ? 'border-rose-500 bg-rose-50/70 shadow-2xs'
                        : 'border-slate-200 bg-white hover:bg-rose-50/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5 font-semibold text-xs text-rose-700">
                        <Siren className="w-4 h-4 text-rose-600 animate-pulse" />
                        <span>Suara Darurat</span>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-600 text-white shadow-2xs">
                        Merah EWS
                      </span>
                    </div>
                    <p className="text-[11px] text-rose-600/80 leading-tight">
                      Sirine bahaya, alarm evakuasi, peringatan gempa/kebakaran, darurat.
                    </p>
                  </div>
                </div>
              </div>

              {/* Tombol Aksi */}
              <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
                <button 
                  type="button" 
                  onClick={() => {
                    setShowUploadModal(false);
                    setUploadSelectedFile(null);
                  }}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  Batal
                </button>
                <button 
                  type="submit" 
                  disabled={!uploadSelectedFile || isUploading}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white shadow-xs transition-all cursor-pointer disabled:opacity-50 ${
                    uploadCategory === 'darurat'
                      ? 'bg-rose-600 hover:bg-rose-700'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>{isUploading ? 'Mengunggah...' : uploadCategory === 'darurat' ? 'Unggah Suara Darurat' : 'Unggah Suara'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: KELOLA GROUP SPEAKER                               */}
      {/* ========================================================= */}
      {showGroupModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-lg max-h-[85vh] flex flex-col p-5 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900">Kelola Group Speaker</h3>
                  <p className="text-xs text-slate-500">Tambah group baru, ubah nama group, atau hapus group</p>
                </div>
              </div>
              <button 
                onClick={() => {
                  setShowGroupModal(false);
                  setEditingGroupOldName(null);
                }} 
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-4.5 h-4.5" />
              </button>
            </div>

            {/* Form Tambah Group */}
            <form onSubmit={handleCreateGroup} className="mt-4 flex gap-2">
              <input
                type="text"
                placeholder="Nama group baru (misal: Workshop, Dermaga 2...)"
                value={newGroupName}
                onChange={e => setNewGroupName(e.target.value)}
                className="flex-1 px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
              />
              <button
                type="submit"
                disabled={!newGroupName.trim()}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white shadow-xs transition-all cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Tambah</span>
              </button>
            </form>

            {/* List of Groups */}
            <div className="flex-1 overflow-y-auto space-y-2 mt-4 text-xs pr-1">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-1">
                Daftar Group Aktif ({groupsList.length})
              </div>
              {groupsList.length === 0 ? (
                <div className="p-6 text-center text-slate-400 text-xs">
                  Belum ada group terdaftar.
                </div>
              ) : (
                groupsList.map((g) => {
                  const speakerCount = speakers.filter(s => getSpeakerGroups(s).includes(g)).length;
                  const isEditing = editingGroupOldName === g;

                  return (
                    <div 
                      key={g} 
                      className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between gap-2 transition-all hover:bg-slate-100/60"
                    >
                      {isEditing ? (
                        <div className="flex-1 flex items-center gap-2">
                          <input
                            type="text"
                            value={editingGroupNewName}
                            onChange={e => setEditingGroupNewName(e.target.value)}
                            onKeyDown={e => {
                              if (e.key === 'Enter') handleUpdateGroup(g, editingGroupNewName);
                              if (e.key === 'Escape') setEditingGroupOldName(null);
                            }}
                            autoFocus
                            className="flex-1 px-2.5 py-1.5 rounded-lg border border-blue-400 bg-white text-xs outline-hidden focus:ring-1 focus:ring-blue-500"
                          />
                          <button
                            type="button"
                            onClick={() => handleUpdateGroup(g, editingGroupNewName)}
                            className="px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs cursor-pointer shadow-xs"
                          >
                            Simpan
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingGroupOldName(null)}
                            className="px-2.5 py-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 font-medium text-xs cursor-pointer"
                          >
                            Batal
                          </button>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center gap-2.5 min-w-0">
                            <span className="font-semibold text-slate-800 truncate">{g}</span>
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-white border border-slate-200 text-slate-500">
                              {speakerCount} Speaker
                            </span>
                          </div>

                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingGroupOldName(g);
                                setEditingGroupNewName(g);
                              }}
                              className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-white transition-colors cursor-pointer"
                              title="Ubah nama group"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteGroup(g)}
                              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-white transition-colors cursor-pointer"
                              title="Hapus group"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            <div className="pt-3 mt-3 border-t border-slate-100 flex justify-end">
              <button 
                type="button" 
                onClick={() => {
                  setShowGroupModal(false);
                  setEditingGroupOldName(null);
                }}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors cursor-pointer"
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: PENGATURAN JARINGAN MULTICAST                      */}
      {/* ========================================================= */}
      {showSettings && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-md p-5 shadow-xl">
            <div className="flex items-center justify-between mb-3.5">
              <h3 className="text-base font-semibold text-slate-900">Pengaturan Jaringan</h3>
              <button onClick={() => setShowSettings(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4.5 h-4.5" />
              </button>
            </div>

            <form onSubmit={handleSaveSettings} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Alamat IP Multicast</label>
                <input 
                  type="text" 
                  value={settings.multicast_ip || ''}
                  onChange={e => setSettings({ ...settings, multicast_ip: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Port UDP Multicast</label>
                <input 
                  type="text" 
                  value={settings.multicast_port || ''}
                  onChange={e => setSettings({ ...settings, multicast_port: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                />
              </div>

              <div className="pt-1.5 flex justify-end gap-2">
                <button 
                  type="button" 
                  onClick={() => setShowSettings(false)}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100"
                >
                  Tutup
                </button>
                <button 
                  type="submit" 
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
                >
                  Simpan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
