import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  ChevronDown, Play, Square, Volume2, Radio, Clock, Music, 
  Upload, Trash2, Settings, Plus, RefreshCw, Bell, 
  Siren, HardHat, Copy, History, X, Search, 
  Wifi, Activity, Check, Calendar,
  Headphones, Pause,
  Layers, Edit2, AlertTriangle, ArrowRight, Laptop, Users
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
  const currentLabel = selectedOption ? selectedOption.label : placeholder;

  return (
    <div className={`relative ${className ? className : 'inline-block'} min-w-0`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        title={currentLabel}
        className={`flex items-center justify-between gap-2 rounded-xl transition-all font-medium text-xs cursor-pointer outline-hidden select-none min-w-0 overflow-hidden ${
          size === 'sm' ? 'px-2.5 py-1.5' : 'px-3 py-2'
        } ${
          isDark
            ? 'bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 hover:border-slate-600 focus:ring-1 focus:ring-blue-400 shadow-xs'
            : 'bg-slate-50 text-slate-700 border border-slate-200 hover:bg-white hover:border-slate-300 focus:ring-2 focus:ring-blue-500/20 shadow-2xs'
        } ${buttonClassName}`}
      >
        <span className="min-w-0 flex-1 flex items-center gap-1.5 overflow-hidden">
          {selectedOption?.icon}
          <span className="truncate block min-w-0">{currentLabel}</span>
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

// REUSABLE MULTI-TARGET SELECTOR (BISA CENTANG GROUP + SPEAKER SEKALIGUS)
function MultiTargetSelector({
  targetMode = 'all', // 'all' | 'group' | 'speaker' | 'custom' | 'hybrid'
  selectedGroups = [], // string[]
  selectedSpeakerIds = [], // number[]
  onChange, // ({ targetMode, selectedGroups, selectedSpeakerIds }) => void
  speakers = [],
  groupsList = [],
  variant = 'light', // 'dark' | 'light'
  size = 'sm',
  className = '',
  buttonClassName = '',
  placeholder = 'Pilih Target Siaran',
  align = 'right' // 'right' (buka ke kiri) | 'left' (buka ke kanan)
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [speakerSearch, setSpeakerSearch] = useState('');
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

  // Active groups with speakers
  const activeGroupsWithSpeakers = useMemo(() => {
    return groupsList.filter(g => 
      speakers.some(s => {
        const sGrps = (s.groups && Array.isArray(s.groups) ? s.groups : [s.zone || '']).map(x => String(x).toLowerCase());
        return sGrps.includes(g.toLowerCase());
      })
    );
  }, [groupsList, speakers]);

  // Online count
  const onlineCount = useMemo(() => speakers.filter(s => s.status === 'online').length, [speakers]);

  // Filtered speakers by search term
  const filteredSpeakers = useMemo(() => {
    if (!speakerSearch.trim()) return speakers;
    const q = speakerSearch.toLowerCase();
    return speakers.filter(s => 
      (s.name && s.name.toLowerCase().includes(q)) || 
      (s.ip_address && s.ip_address.includes(q)) ||
      (s.zone && s.zone.toLowerCase().includes(q))
    );
  }, [speakers, speakerSearch]);

  const isAllSelected = selectedGroups.length === 0 && selectedSpeakerIds.length === 0;

  // Dynamic summary label on trigger button
  const summaryLabel = useMemo(() => {
    if (isAllSelected) {
      return `Semua Speaker (${speakers.length} spk)`;
    }
    if (selectedGroups.length > 0 && selectedSpeakerIds.length > 0) {
      if (selectedGroups.length === 1 && selectedSpeakerIds.length === 1) {
        const spk = speakers.find(s => s.id === selectedSpeakerIds[0]);
        return `${selectedGroups[0]} + ${spk ? spk.name : '1 Spk'}`;
      }
      return `${selectedGroups.length} Group + ${selectedSpeakerIds.length} Spk`;
    }
    if (selectedGroups.length > 0) {
      if (selectedGroups.length === 1) return `Group: ${selectedGroups[0]}`;
      if (selectedGroups.length === 2) return `${selectedGroups[0]} + ${selectedGroups[1]}`;
      return `${selectedGroups.length} Group Terpilih`;
    }
    if (selectedSpeakerIds.length > 0) {
      if (selectedSpeakerIds.length === 1) {
        const sp = speakers.find(s => s.id === selectedSpeakerIds[0]);
        return sp ? `Speaker: ${sp.name}` : `1 Speaker Terpilih`;
      }
      if (selectedSpeakerIds.length === 2) {
        const sp1 = speakers.find(s => s.id === selectedSpeakerIds[0]);
        const sp2 = speakers.find(s => s.id === selectedSpeakerIds[1]);
        return `${sp1?.name || 'Spk 1'} + ${sp2?.name || 'Spk 2'}`;
      }
      return `${selectedSpeakerIds.length} Speaker Terpilih`;
    }
    return placeholder;
  }, [isAllSelected, selectedGroups, selectedSpeakerIds, speakers, placeholder]);

  // Handlers
  const handleSelectAllGlobal = () => {
    onChange({
      targetMode: 'all',
      selectedGroups: [],
      selectedSpeakerIds: []
    });
  };

  const handleToggleGroup = (groupName) => {
    const exists = selectedGroups.includes(groupName);
    const nextGroups = exists
      ? selectedGroups.filter(g => g !== groupName)
      : [...selectedGroups, groupName];
    
    let nextMode = 'all';
    if (nextGroups.length > 0 && selectedSpeakerIds.length > 0) nextMode = 'hybrid';
    else if (nextGroups.length > 0) nextMode = 'group';
    else if (selectedSpeakerIds.length > 0) nextMode = 'speaker';

    onChange({
      targetMode: nextMode,
      selectedGroups: nextGroups,
      selectedSpeakerIds
    });
  };

  const handleSelectAllGroups = () => {
    const nextGroups = [...activeGroupsWithSpeakers];
    const nextMode = selectedSpeakerIds.length > 0 ? 'hybrid' : 'group';
    onChange({
      targetMode: nextMode,
      selectedGroups: nextGroups,
      selectedSpeakerIds
    });
  };

  const handleClearGroups = () => {
    const nextMode = selectedSpeakerIds.length > 0 ? 'speaker' : 'all';
    onChange({
      targetMode: nextMode,
      selectedGroups: [],
      selectedSpeakerIds
    });
  };

  const handleToggleSpeaker = (spkId) => {
    const exists = selectedSpeakerIds.includes(spkId);
    const nextIds = exists
      ? selectedSpeakerIds.filter(id => id !== spkId)
      : [...selectedSpeakerIds, spkId];

    let nextMode = 'all';
    if (selectedGroups.length > 0 && nextIds.length > 0) nextMode = 'hybrid';
    else if (nextIds.length > 0) nextMode = 'speaker';
    else if (selectedGroups.length > 0) nextMode = 'group';

    onChange({
      targetMode: nextMode,
      selectedGroups,
      selectedSpeakerIds: nextIds
    });
  };

  const handleSelectAllSpeakers = () => {
    const nextIds = speakers.map(s => s.id);
    const nextMode = selectedGroups.length > 0 ? 'hybrid' : 'speaker';
    onChange({
      targetMode: nextMode,
      selectedGroups,
      selectedSpeakerIds: nextIds
    });
  };

  const handleClearSpeakers = () => {
    const nextMode = selectedGroups.length > 0 ? 'group' : 'all';
    onChange({
      targetMode: nextMode,
      selectedGroups,
      selectedSpeakerIds: []
    });
  };

  const isDark = variant === 'dark';

  return (
    <div className={`relative ${className ? className : 'inline-block'} min-w-0`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        title={summaryLabel}
        className={`flex items-center justify-between gap-2 rounded-xl transition-all font-medium text-xs cursor-pointer outline-hidden select-none min-w-0 overflow-hidden ${
          size === 'sm' ? 'px-2.5 py-1.5' : 'px-3 py-2'
        } ${
          isDark
            ? 'bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 hover:border-slate-600 focus:ring-1 focus:ring-blue-400 shadow-xs'
            : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 hover:border-slate-300 focus:ring-2 focus:ring-blue-500/20 shadow-2xs'
        } ${buttonClassName}`}
      >
        <span className="min-w-0 flex-1 flex items-center gap-1.5 overflow-hidden">
          {isAllSelected ? (
            <Radio className="w-3.5 h-3.5 text-blue-500 shrink-0" />
          ) : selectedGroups.length > 0 && selectedSpeakerIds.length > 0 ? (
            <Volume2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
          ) : selectedGroups.length > 0 ? (
            <Users className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
          ) : (
            <Volume2 className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          )}
          <span className="truncate block min-w-0">{summaryLabel}</span>
        </span>
        <ChevronDown className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 ${
          isDark ? 'text-slate-400' : 'text-slate-500'
        } ${isOpen ? 'rotate-180 text-blue-500' : ''}`} />
      </button>

      {isOpen && (
        <div
          className={`absolute ${align === 'right' ? 'right-0' : 'left-0'} top-full mt-1.5 w-84 sm:w-96 max-w-[92vw] rounded-2xl p-3.5 z-50 shadow-2xl border animate-in fade-in zoom-in-95 duration-100 ${
            isDark
              ? 'bg-slate-900 border-slate-700/80 text-slate-200 ring-1 ring-white/10'
              : 'bg-white border-slate-200 text-slate-700 shadow-xl'
          }`}
          style={{ minWidth: '320px' }}
        >
          {/* Header & Global Broadcast Option */}
          <div className="mb-3">
            <div className={`flex items-center justify-between pb-2 mb-2 border-b ${
              isDark ? 'border-slate-800' : 'border-slate-100'
            }`}>
              <span className={`text-xs font-semibold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                Target Siaran
              </span>
              <button
                type="button"
                onClick={handleSelectAllGlobal}
                className={`text-[11px] px-2.5 py-1 rounded-lg font-medium cursor-pointer transition-colors ${
                  isAllSelected
                    ? 'bg-blue-600 text-white'
                    : isDark ? 'bg-slate-800 text-slate-300 hover:bg-slate-700' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                Semua Speaker Global
              </button>
            </div>
            
            <p className="text-[11px] text-slate-400">
              Pilih group atau speaker spesifik untuk siaran gabungan, contoh: 1 Group dan 1 Speaker.
            </p>
          </div>

          <div className="max-h-72 overflow-y-auto space-y-3.5 pr-1">
            {/* SEKSI 1: PILIH GROUP */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className={`font-semibold flex items-center gap-1.5 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  <Users className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Group Area • {selectedGroups.length} dipilih</span>
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSelectAllGroups}
                    className="text-blue-500 hover:underline cursor-pointer font-medium text-[10px]"
                  >
                    Pilih Semua
                  </button>
                  <span className="text-slate-400">•</span>
                  <button
                    type="button"
                    onClick={handleClearGroups}
                    className="text-slate-400 hover:text-rose-500 cursor-pointer text-[10px]"
                  >
                    Kosongkan
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {activeGroupsWithSpeakers.length === 0 ? (
                  <div className="col-span-2 text-center py-2 text-[11px] text-slate-400">
                    Tidak ada group aktif.
                  </div>
                ) : (
                  activeGroupsWithSpeakers.map((grp) => {
                    const isChecked = selectedGroups.includes(grp);
                    const grpSpeakers = speakers.filter(s => {
                      const sGrps = (s.groups && Array.isArray(s.groups) ? s.groups : [s.zone || '']).map(x => String(x).toLowerCase());
                      return sGrps.includes(grp.toLowerCase());
                    });

                    return (
                      <label
                        key={grp}
                        className={`flex items-center justify-between gap-1.5 p-2 rounded-xl text-xs cursor-pointer transition-all border ${
                          isChecked
                            ? isDark
                              ? 'bg-blue-950/40 border-blue-500/40 text-blue-200'
                              : 'bg-blue-50 border-blue-200 text-blue-900 font-medium'
                            : isDark
                              ? 'bg-slate-800/40 border-slate-700/40 text-slate-300 hover:bg-slate-800'
                              : 'bg-white border-slate-200/80 text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 min-w-0">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => handleToggleGroup(grp)}
                            className="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer w-3.5 h-3.5"
                          />
                          <span className="truncate">{grp}</span>
                        </div>
                        <span className="text-[10px] text-slate-400 shrink-0">
                          {grpSpeakers.length} spk
                        </span>
                      </label>
                    );
                  })
                )}
              </div>
            </div>

            {/* SEKSI 2: PILIH SPEAKER SPESIFIK */}
            <div className={`space-y-1.5 pt-2.5 border-t ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
              <div className="flex items-center justify-between text-[11px]">
                <span className={`font-semibold flex items-center gap-1.5 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  <Volume2 className="w-3.5 h-3.5 text-amber-500" />
                  <span>Speaker Spesifik • {selectedSpeakerIds.length} dipilih</span>
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSelectAllSpeakers}
                    className="text-blue-500 hover:underline cursor-pointer font-medium text-[10px]"
                  >
                    Pilih Semua
                  </button>
                  <span className="text-slate-400">•</span>
                  <button
                    type="button"
                    onClick={handleClearSpeakers}
                    className="text-slate-400 hover:text-rose-500 cursor-pointer text-[10px]"
                  >
                    Kosongkan
                  </button>
                </div>
              </div>

              {/* Speaker Search bar */}
              {speakers.length > 4 && (
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Cari speaker atau IP..."
                    value={speakerSearch}
                    onChange={(e) => setSpeakerSearch(e.target.value)}
                    className={`w-full pl-8 pr-3 py-1.5 rounded-lg border text-xs outline-hidden ${
                      isDark
                        ? 'bg-slate-800/80 border-slate-700 text-slate-200 placeholder-slate-500 focus:border-blue-500'
                        : 'bg-slate-50 border-slate-200 text-slate-800 placeholder-slate-400 focus:bg-white focus:border-blue-500'
                    }`}
                  />
                </div>
              )}

              <div className="space-y-1">
                {filteredSpeakers.length === 0 ? (
                  <div className="text-center py-2 text-[11px] text-slate-400">
                    Tidak ada speaker yang sesuai pencarian.
                  </div>
                ) : (
                  filteredSpeakers.map((spk) => {
                    const isChecked = selectedSpeakerIds.includes(spk.id);
                    const isOnline = spk.status === 'online';

                    return (
                      <label
                        key={spk.id}
                        className={`flex items-center justify-between gap-2 p-1.5 rounded-xl text-xs cursor-pointer transition-all border ${
                          isChecked
                            ? isDark
                              ? 'bg-blue-950/40 border-blue-500/40 text-blue-200'
                              : 'bg-blue-50 border-blue-200 text-blue-900 font-medium'
                            : isDark
                              ? 'bg-slate-800/40 border-slate-700/40 text-slate-300 hover:bg-slate-800'
                              : 'bg-white border-slate-200/80 text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => handleToggleSpeaker(spk.id)}
                            className="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer w-3.5 h-3.5"
                          />
                          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isOnline ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                          <div className="flex items-center gap-1.5 min-w-0">
                            <span className="truncate">{spk.name}</span>
                            {spk.hostname && (
                              <span className="text-[10px] text-slate-400 font-mono shrink-0">
                                • {spk.hostname}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {spk.device_type === 'node' && (
                            <span className="text-[9px] px-1 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-200">
                              PC
                            </span>
                          )}
                          <span className="text-[10px] text-slate-400 font-mono">
                            {spk.ip_address}
                          </span>
                        </div>
                      </label>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Footer Popover */}
          <div className={`flex items-center justify-between pt-2.5 mt-2.5 border-t text-xs ${
            isDark ? 'border-slate-800' : 'border-slate-100'
          }`}>
            <span className="text-[11px] text-slate-500 font-medium truncate max-w-[220px]">
              {isAllSelected
                ? 'Target: Semua Speaker'
                : selectedGroups.length > 0 && selectedSpeakerIds.length > 0
                ? `Target: ${selectedGroups.length} Group + ${selectedSpeakerIds.length} Speaker`
                : selectedGroups.length > 0
                ? `Target: ${selectedGroups.length} Group`
                : `Target: ${selectedSpeakerIds.length} Speaker`}
            </span>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs cursor-pointer shadow-xs transition-colors"
            >
              Selesai
            </button>
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
    target_desc: 'Semua Speaker Global'
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
  const [selectedGroup, setSelectedGroup] = useState('');
  const [selectedGroups, setSelectedGroups] = useState([]);
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
  const [triggeringScheduleId, setTriggeringScheduleId] = useState(null);
  const isActionBusyRef = useRef(false);
  const [isPlayingToSpeakers, setIsPlayingToSpeakers] = useState(false);
  const [isSavingSchedule, setIsSavingSchedule] = useState(false);
  const [isSavingSpeaker, setIsSavingSpeaker] = useState(false);

  // Modals & Navigation
  const [activeMainTab, setActiveMainTab] = useState('schedules'); // 'schedules' | 'audio'
  const [showSpeakerMonitorModal, setShowSpeakerMonitorModal] = useState(false);
  const [showAddSchedule, setShowAddSchedule] = useState(false);
  const [editingScheduleId, setEditingScheduleId] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showLogsModal, setShowLogsModal] = useState(false);
  const [showSpeakerModal, setShowSpeakerModal] = useState(false);
  const [showSirenConfirmModal, setShowSirenConfirmModal] = useState(false);
  const [playConfirmAudio, setPlayConfirmAudio] = useState(null);
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
    enable_local: 'true',
    siren_audio_filename: 'sirine_ews_test.wav',
    k3_audio_filename: 'safety_k3_chime.wav'
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
    target_speakers: '',
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

  // Server Time Synchronization & Display (Rock-solid, zero wobble, no font-mono)
  const serverOffsetRef = useRef(0);
  const [serverHours, setServerHours] = useState('12');
  const [serverMinutes, setServerMinutes] = useState('00');
  const [serverSeconds, setServerSeconds] = useState('00');
  const [serverTimeDisplay, setServerTimeDisplay] = useState('');
  const [serverDateDisplay, setServerDateDisplay] = useState('');

  // Fetch initial server time offset
  useEffect(() => {
    const syncServerTime = async () => {
      try {
        const start = Date.now();
        const res = await fetch('/api/time');
        if (res.ok) {
          const data = await res.json();
          const latency = (Date.now() - start) / 2;
          const serverMs = (data.timestamp * 1000) + latency;
          serverOffsetRef.current = serverMs - Date.now();
        }
      } catch (err) {
        console.error('Failed to sync server time', err);
      }
    };

    syncServerTime();
    // Sync every 3 minutes
    const syncInterval = setInterval(syncServerTime, 3 * 60 * 1000);
    return () => clearInterval(syncInterval);
  }, []);

  // Realtime clock ticking based on server offset
  useEffect(() => {
    const updateClock = () => {
      const serverNow = new Date(Date.now() + serverOffsetRef.current);
      const hours = String(serverNow.getHours()).padStart(2, '0');
      const minutes = String(serverNow.getMinutes()).padStart(2, '0');
      const seconds = String(serverNow.getSeconds()).padStart(2, '0');
      setServerHours(hours);
      setServerMinutes(minutes);
      setServerSeconds(seconds);
      setServerTimeDisplay(`${hours}:${minutes}:${seconds}`);
      setCurrentTime(`${hours}:${minutes}:${seconds} WIB`);

      setServerDateDisplay(serverNow.toLocaleDateString('id-ID', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      }));
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

  // Refetch logs whenever the audit modal is opened
  useEffect(() => {
    if (showLogsModal) {
      fetch('/api/logs')
        .then(r => r.json())
        .then(data => setLogs(data || []))
        .catch(err => console.error('Failed to fetch logs', err));
    }
  }, [showLogsModal]);

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
    if (targetMode === 'hybrid') {
      const grpPart = selectedGroups.length > 0 ? selectedGroups.join(', ') : '';
      const spkPart = selectedSpeakerIds.length > 0 ? `${selectedSpeakerIds.length} Spk` : '';
      return [grpPart, spkPart].filter(Boolean).join(' + ') || 'Semua Speaker';
    }
    if (targetMode === 'group' || targetMode === 'zone') {
      const grp = selectedGroups[0] || selectedGroup;
      const grpSpeakers = speakers.filter(s => getSpeakerGroups(s).includes(grp));
      const onCount = grpSpeakers.filter(s => s.status === 'online').length;
      return `Group: ${selectedGroups.length > 1 ? selectedGroups.join(', ') : grp} (${grpSpeakers.length} speaker • ${onCount} online)`;
    }
    if (targetMode === 'speaker') {
      if (selectedSpeakerIds.length > 1) {
        return `${selectedSpeakerIds.length} Speaker Terpilih`;
      }
      const spId = selectedSpeakerIds[0] || selectedSpeakerId;
      const sp = speakers.find(s => s.id === spId);
      if (sp) {
        return `Speaker ${sp.name} (${sp.status === 'online' ? 'Online' : 'Offline'})`;
      }
    }
    return 'Semua Speaker';
  }, [targetMode, selectedGroup, selectedGroups, selectedSpeakerId, selectedSpeakerIds, speakers, onlineCount]);

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

  // Helper build target payload for server broadcast (Hybrid support)
  const buildTargetPayload = () => {
    const hasGroups = selectedGroups && selectedGroups.length > 0;
    const hasSpeakers = selectedSpeakerIds && selectedSpeakerIds.length > 0;

    if (!hasGroups && !hasSpeakers) {
      return { target_mode: 'all' };
    }

    let mode = 'all';
    if (hasGroups && hasSpeakers) mode = 'hybrid';
    else if (hasGroups) mode = 'group';
    else if (hasSpeakers) mode = 'speaker';

    return {
      target_mode: mode,
      target_groups: selectedGroups || [],
      target_group: (selectedGroups || []).join(', '),
      target_zone: (selectedGroups || []).join(', '),
      speaker_ids: selectedSpeakerIds || [],
      speaker_id: (selectedSpeakerIds && selectedSpeakerIds[0]) ? selectedSpeakerIds[0] : null
    };
  };

  // Play audio to Outside Physical Speakers (Server Broadcast)
  const handlePlayToSpeakers = async (audioId) => {
    if (isActionBusyRef.current) return;
    isActionBusyRef.current = true;
    setIsPlayingToSpeakers(true);
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
    } finally {
      setTimeout(() => {
        isActionBusyRef.current = false;
        setIsPlayingToSpeakers(false);
      }, 700);
    }
  };

  // Play audio filename to Outside Physical Speakers
  const handlePlayFilenameToSpeakers = async (filename) => {
    if (isActionBusyRef.current) return;
    isActionBusyRef.current = true;
    setIsPlayingToSpeakers(true);
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
    } finally {
      setTimeout(() => {
        isActionBusyRef.current = false;
        setIsPlayingToSpeakers(false);
      }, 700);
    }
  };

  // Stop Field Broadcast
  const handleStop = async () => {
    if (isActionBusyRef.current) return;
    isActionBusyRef.current = true;
    try {
      await fetch('/api/stop', { method: 'POST' });
      fetchData();
    } catch (err) {
      alert('Gagal menghentikan siaran: ' + err);
    } finally {
      setTimeout(() => {
        isActionBusyRef.current = false;
      }, 500);
    }
  };

  // Stop a specific active broadcast session
  const handleStopSession = async (sessionId, e) => {
    if (e) e.stopPropagation();
    try {
      await fetch(`/api/playback/sessions/${sessionId}/stop`, { method: 'POST' });
      fetchData();
    } catch (err) {
      console.error('Gagal menghentikan sesi:', err);
    }
  };

  // Delete an item from playback queue
  const handleDeleteQueueItem = async (queueId, e) => {
    if (e) e.stopPropagation();
    try {
      await fetch(`/api/playback/queue/${queueId}`, { method: 'DELETE' });
      fetchData();
    } catch (err) {
      console.error('Gagal menghapus antrean:', err);
    }
  };

  // Trigger Schedule Manually according to its own target
  const handleTriggerSchedule = async (schedule) => {
    if (isActionBusyRef.current || triggeringScheduleId) return;
    isActionBusyRef.current = true;
    handleStopBrowserPreview();
    setTriggeringScheduleId(schedule.id);
    try {
      const res = await fetch(`/api/schedules/${schedule.id}/trigger`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        alert('Gagal menyiarkan jadwal: ' + (errData.detail || res.statusText || 'Server Error'));
      }
      fetchData();
    } catch (err) {
      alert('Gagal menyiarkan jadwal: ' + err);
    } finally {
      setTimeout(() => {
        isActionBusyRef.current = false;
        setTriggeringScheduleId(null);
      }, 1500);
    }
  };

  // Trigger Scan All Speakers
  const handleScanAll = async () => {
    if (isScanning || isActionBusyRef.current) return;
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
    if (isActionBusyRef.current || testingSpeakerId) return;
    isActionBusyRef.current = true;
    handleStopBrowserPreview();
    setTestingSpeakerId(speaker.id);
    try {
      await fetch(`/api/speakers/${speaker.id}/test-audio`, { method: 'POST' });
    } catch (err) {
      alert(`Gagal tes suara ke ${speaker.name}: ${err}`);
    } finally {
      setTimeout(() => {
        isActionBusyRef.current = false;
        setTestingSpeakerId(null);
      }, 2000);
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
    if (isSavingSpeaker) return;
    setIsSavingSpeaker(true);
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
    } finally {
      setIsSavingSpeaker(false);
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
      target_speakers: '',
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
      target_speakers: schedule.target_speakers || '',
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
      target_speakers: schedule.target_speakers || '',
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
    if (isSavingSchedule) return;
    setIsSavingSchedule(true);
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
    } finally {
      setIsSavingSchedule(false);
    }
  };

  // Audio Upload & Category Handlers
  const handleOpenUploadModal = (preselectedFile = null) => {
    if (preselectedFile) {
      setUploadSelectedFile(preselectedFile);
      const cleanName = preselectedFile.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' ');
      setUploadDisplayName(cleanName);
      const isEmerg = /siren|sirine|ews|darurat|emergency|bahaya|evakuasi|kebakaran|gempa|tsunami/i.test(preselectedFile.name);
      const isSafety = /safety|k3|briefing|apd|keselamatan/i.test(preselectedFile.name);
      setUploadCategory(isEmerg ? 'darurat' : isSafety ? 'safety' : 'biasa');
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
    const isEmerg = /siren|sirine|ews|darurat|emergency|bahaya|evakuasi|kebakaran|gempa|tsunami/i.test(file.name);
    const isSafety = /safety|k3|briefing|apd|keselamatan/i.test(file.name);
    if (isEmerg) setUploadCategory('darurat');
    else if (isSafety) setUploadCategory('safety');
    else setUploadCategory('biasa');
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
    const targetCategory = explicitTarget || currentCat;
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
        await fetchData();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Gagal memperbarui kategori audio');
      }
    } catch (err) {
      alert('Gagal menghubungi server');
    }
  };

  const handleCycleCategory = async (audio, e) => {
    if (e) e.stopPropagation();
    const currentCat = audio.category || 'biasa';
    const nextCat = currentCat === 'biasa' ? 'safety' : currentCat === 'safety' ? 'darurat' : 'biasa';
    try {
      const res = await fetch(`/api/audio/${audio.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: nextCat })
      });
      if (res.ok) {
        await fetchData();
      }
    } catch (err) {
      console.error('Gagal mengubah prioritas audio:', err);
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

  // Helper target label for schedule badge in table
  const getScheduleTargetBadge = (s) => {
    const grp = (s.target_group || s.target_zone || '').trim();
    const rawSpkIds = (s.target_speakers ? s.target_speakers.split(',') : (s.target_speaker_id ? [s.target_speaker_id] : []))
      .map(x => parseInt(String(x).trim(), 10))
      .filter(Boolean);
    const grpList = grp ? grp.split(',').map(x => x.trim()).filter(Boolean) : [];

    if (s.target_mode === 'all' || (!grpList.length && !rawSpkIds.length)) {
      return 'Semua Speaker';
    }

    // Hybrid: Group + Speaker
    if (grpList.length > 0 && rawSpkIds.length > 0) {
      if (grpList.length === 1 && rawSpkIds.length === 1) {
        const sp = speakers.find(x => x.id === rawSpkIds[0]);
        return `${grpList[0]} + ${sp?.name || `Spk ${rawSpkIds[0]}`}`;
      }
      return `${grpList.length} Group + ${rawSpkIds.length} Spk`;
    }

    // Group only
    if (grpList.length > 0) {
      if (grpList.length === 1) return `Group: ${grpList[0]}`;
      if (grpList.length === 2) return `${grpList[0]} + ${grpList[1]}`;
      return `${grpList.length} Group Terpilih`;
    }

    // Speaker only
    if (rawSpkIds.length > 0) {
      if (rawSpkIds.length === 1) {
        const sp = speakers.find(x => x.id === rawSpkIds[0]);
        return `Speaker: ${sp?.name || `ID ${rawSpkIds[0]}`}`;
      }
      if (rawSpkIds.length === 2) {
        const sp1 = speakers.find(x => x.id === rawSpkIds[0]);
        const sp2 = speakers.find(x => x.id === rawSpkIds[1]);
        return `${sp1?.name || 'Spk 1'} + ${sp2?.name || 'Spk 2'}`;
      }
      return `${rawSpkIds.length} Speaker Terpilih`;
    }

    return 'Semua Speaker';
  };

  const isPlaying = playback.status === 'STREAMING' || playback.status === 'PLAYING';
  const activeSessions = Array.isArray(playback.active_sessions) ? playback.active_sessions : [];
  const activeQueue = Array.isArray(playback.queue) ? playback.queue : [];
  const hasMultipleSessions = activeSessions.length > 1;

  const hasEmergency = isPlaying && (
    activeSessions.some(s => s.priority === 1 || (s.category || '').toLowerCase() === 'darurat' || (s.title || '').toLowerCase().includes('sirine') || (s.title || '').toLowerCase().includes('darurat') || (s.title || '').toLowerCase().includes('ews')) ||
    (playback.title || '').toLowerCase().includes('sirine') || 
    (playback.title || '').toLowerCase().includes('darurat') ||
    (playback.title || '').toLowerCase().includes('ews')
  );

  const hasSafety = isPlaying && !hasEmergency && (
    activeSessions.some(s => s.priority === 2 || (s.category || '').toLowerCase() === 'safety' || (s.title || '').toLowerCase().includes('safety') || (s.title || '').toLowerCase().includes('k3')) ||
    (playback.category || '').toLowerCase() === 'safety'
  );

  const barBgClass = hasEmergency
    ? 'bg-rose-700 text-white border-rose-800'
    : hasSafety
      ? 'bg-amber-600 text-white border-amber-700'
      : isPlaying
        ? 'bg-blue-600 text-white border-blue-700'
        : 'bg-white text-slate-800 border-slate-200/90 shadow-2xs';

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* STICKY TOP CONTAINER: HEADER + COLORBAR */}
      <div className="sticky top-0 z-30 shadow-xs">
        {/* 1. TOP HEADER (COMPACT & CLEAN) */}
        <header className="bg-white border-b border-slate-200/90">
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

      {/* 2. ACTIVE BROADCAST BAR (STATUS + SOUNDBOARD MINI / MULTI-ZONE SESSIONS) */}
      <section className={`border-b transition-colors ${barBgClass}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 min-h-15 py-2.5 flex flex-wrap items-center justify-between gap-3">
          {/* Status Pill & Live Info */}
          <div className="flex items-center gap-2.5 min-w-0 flex-1 flex-wrap">
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold shrink-0 ${
              hasEmergency
                ? 'bg-rose-800 text-white border border-rose-500'
                : hasSafety
                  ? 'bg-amber-700 text-white border border-amber-500'
                  : isPlaying
                    ? 'bg-blue-700 text-white border border-blue-500'
                    : 'bg-slate-100 text-slate-700 border border-slate-200/90'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                hasEmergency 
                  ? 'bg-white animate-ping' 
                  : isPlaying 
                    ? 'bg-emerald-400 animate-pulse' 
                    : 'bg-emerald-500'
              }`} />
              {hasEmergency 
                ? (hasMultipleSessions ? `Darurat • ${activeSessions.length} Zona` : 'Darurat')
                : hasSafety
                  ? (hasMultipleSessions ? `K3 • ${activeSessions.length} Zona` : 'K3')
                  : isPlaying 
                    ? (hasMultipleSessions ? `Berbunyi • ${activeSessions.length} Zona` : 'Berbunyi')
                    : 'Siaga'}
            </span>

            {isPlaying ? (
              hasMultipleSessions ? (
                /* Multiple Simultaneous Sessions: Render Session Chips */
                <div className="flex items-center gap-2 flex-wrap min-w-0">
                  {activeSessions.map((s) => {
                    const isPrio1 = s.priority === 1 || (s.category || '').toLowerCase() === 'darurat';
                    const isPrio2 = s.priority === 2 || (s.category || '').toLowerCase() === 'safety';
                    return (
                      <div 
                        key={s.session_id} 
                        className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-xl text-xs font-medium border shadow-2xs backdrop-blur-xs ${
                          isPrio1
                            ? 'bg-rose-900/60 border-rose-400 text-rose-100'
                            : isPrio2
                              ? 'bg-amber-900/50 border-amber-300 text-amber-100'
                              : 'bg-black/20 border-white/20 text-white'
                        }`}
                      >
                        <span className="font-semibold text-white/95 truncate max-w-[120px] sm:max-w-[160px]">
                          {s.target_desc}:
                        </span>
                        <span className="truncate max-w-[120px] sm:max-w-[180px]">
                          {s.title}
                        </span>
                        <span className="text-[11px] opacity-80 shrink-0 font-mono">
                          {formatSec(s.elapsed)}/{formatSec(s.duration)}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => handleStopSession(s.session_id, e)}
                          title={`Hentikan sesi ${s.target_desc}`}
                          className="hover:bg-white/20 rounded p-0.5 text-white/80 hover:text-white transition-colors cursor-pointer"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                /* Single Active Session */
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-white/40 hidden md:inline">•</span>
                  <div className="min-w-0">
                    <h2 className="text-sm font-semibold truncate max-w-xs sm:max-w-md text-white">
                      {playback.title}
                    </h2>
                    {playback.target_desc && (
                      <span className="text-[11px] text-white/70 block truncate">
                        Target: {playback.target_desc}
                      </span>
                    )}
                  </div>
                </div>
              )
            ) : (
              /* Idle */
              <>
                <span className="text-slate-300 hidden md:inline">•</span>
                <h2 className="text-sm font-semibold truncate max-w-xs sm:max-w-sm text-slate-800">
                  Server Siap Menyiarkan
                </h2>
              </>
            )}

            {/* Queue Badge if any waiting items */}
            {activeQueue.length > 0 && (
              <span 
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-400/20 text-amber-100 border border-amber-300/40 shrink-0"
                title={`${activeQueue.length} jadwal sedang menunggu giliran speaker: ${activeQueue.map(q => q.title).join(', ')}`}
              >
                <Clock className="w-3 h-3 text-amber-300" />
                <span>+{activeQueue.length} Antrean</span>
              </span>
            )}
          </div>

          {/* Soundboard Mini & Controls */}
          <div className="flex items-center gap-2 shrink-0">
            {isPlaying ? (
              <>
                {!hasMultipleSessions && (
                  <div className="flex items-center gap-2 mr-1">
                    <span className="text-xs font-medium text-white/90 hidden sm:inline">
                      {formatSec(playback.elapsed)} / {formatSec(playback.duration)}
                    </span>
                    <div className="w-16 sm:w-28 bg-black/30 rounded-full h-1.5 overflow-hidden">
                      <div 
                        className="bg-emerald-400 h-full transition-all duration-300"
                        style={{ width: `${playback.duration ? Math.min(100, (playback.elapsed / playback.duration) * 100) : 0}%` }}
                      />
                    </div>
                  </div>
                )}

                <button 
                  onClick={handleStop}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-all shadow-xs cursor-pointer"
                  title="Hentikan semua siaran audio yang sedang aktif"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>{hasMultipleSessions ? 'Hentikan Semua' : 'Hentikan Siaran'}</span>
                </button>
              </>
            ) : (
              <>
                {/* SOUNDBOARD MINI TRIGGER: SIRINE DARURAT */}
                <button
                  onClick={() => setShowSirenConfirmModal(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-all shadow-xs cursor-pointer"
                  title="Siarkan sirine peringatan darurat ke speaker"
                >
                  <Siren className="w-3.5 h-3.5" />
                  <span>Sirine</span>
                </button>

                {/* SOUNDBOARD MINI TRIGGER: PENGINGAT K3 */}
                <button
                  onClick={() => handlePlayFilenameToSpeakers(settings.k3_audio_filename || 'safety_k3_chime.wav')}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-all border border-slate-200 shadow-2xs cursor-pointer"
                  title="Siarkan pengingat K3 ke speaker"
                >
                  <HardHat className="w-3.5 h-3.5 text-emerald-600" />
                  <span>K3</span>
                </button>

                {/* MULTI TARGET SELECTOR (BISA CENTANG MULTI GROUP ATAU MULTI SPEAKER) */}
                <MultiTargetSelector
                  targetMode={targetMode}
                  selectedGroups={selectedGroups}
                  selectedSpeakerIds={selectedSpeakerIds}
                  onChange={({ targetMode: tm, selectedGroups: sg, selectedSpeakerIds: spids }) => {
                    setTargetMode(tm);
                    setSelectedGroups(sg);
                    setSelectedGroup(sg[0] || 'Kantor');
                    setSelectedSpeakerIds(spids);
                    setSelectedSpeakerId(spids[0] || null);
                  }}
                  speakers={speakers}
                  groupsList={groupsList}
                  variant={isPlaying || hasEmergency ? 'dark' : 'light'}
                  size="sm"
                  align="right"
                  buttonClassName="min-w-[150px] max-w-[220px] sm:max-w-[280px]"
                />
              </>
            )}
          </div>
        </div>
      </section>
      </div>

      {/* 3. MAIN WORKSPACE (ALARM-FIRST CONSOLE) */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex-1 w-full space-y-4">
        
        {/* WAKTU SERVER CARD (PROPORSIONAL, ELEGAN, TIDAK KURUS) */}
        <div className="bg-white rounded-2xl border border-slate-200/90 p-5 sm:p-6 shadow-2xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
            {/* Sisi Kiri: Waktu & Tanggal Server */}
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 mb-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Waktu server</span>
              </div>
              
              <div className="flex items-baseline gap-2">
                <div className="flex items-center text-3xl sm:text-4xl md:text-5xl font-semibold text-slate-900 select-none tracking-tight">
                  <span className="inline-block w-[1.1ch] text-center">{serverHours[0]}</span>
                  <span className="inline-block w-[1.1ch] text-center">{serverHours[1]}</span>
                  <span className="inline-block w-[0.8ch] text-center text-slate-400">:</span>
                  <span className="inline-block w-[1.1ch] text-center">{serverMinutes[0]}</span>
                  <span className="inline-block w-[1.1ch] text-center">{serverMinutes[1]}</span>
                  <span className="inline-block w-[0.8ch] text-center text-slate-400">:</span>
                  <span className="inline-block w-[1.1ch] text-center text-slate-500">{serverSeconds[0]}</span>
                  <span className="inline-block w-[1.1ch] text-center text-slate-500">{serverSeconds[1]}</span>
                </div>
                <span className="text-sm font-semibold text-slate-400">
                  WIB
                </span>
              </div>

              <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span>{serverDateDisplay}</span>
                <span className="text-slate-300">•</span>
                <span>Waktu Indonesia Barat • UTC+7</span>
              </div>
            </div>

            {/* Sisi Kanan: Ringkasan Status Sistem (Mengisi Ruang agar Kokoh dan Tidak Kurus) */}
            <div className="grid grid-cols-2 gap-3 sm:gap-4 shrink-0">
              <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50/80 border border-slate-200/60">
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                  <Volume2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[11px] text-slate-400 font-medium">Speaker Aktif</div>
                  <div className="text-sm font-semibold text-slate-800">
                    {onlineCount} <span className="text-xs font-normal text-slate-400">/ {speakers.length} Online</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50/80 border border-slate-200/60">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[11px] text-slate-400 font-medium">Jadwal Siaran</div>
                  <div className="text-sm font-semibold text-slate-800">
                    {schedules.filter(s => s.enabled).length} <span className="text-xs font-normal text-slate-400">Aktif</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

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
                    {nextSchedule.time_str} • {nextSchedule.name} • {nextSchedule.dayLabel}
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
                            <td className="py-3 px-4 whitespace-nowrap">
                              {(() => {
                                const allTimes = parseScheduleTimes(s.time_str);
                                if (allTimes.length === 1) {
                                  return (
                                    <span 
                                      className={`text-xl font-semibold tracking-tight ${
                                        s.enabled ? 'text-slate-900' : 'text-slate-400'
                                      }`}
                                    >
                                      {allTimes[0]}
                                    </span>
                                  );
                                }

                                const maxVisible = 2;
                                const visibleTimes = allTimes.slice(0, maxVisible);
                                const hasMore = allTimes.length > maxVisible;

                                return (
                                  <div 
                                    className="inline-flex items-center gap-1.5 whitespace-nowrap min-w-0" 
                                    title={`Semua jam siar: ${allTimes.join(', ')}`}
                                  >
                                    {visibleTimes.map((t, idx) => (
                                      <span 
                                        key={idx}
                                        className={`px-2 py-0.5 rounded-md text-xs font-semibold tracking-normal border ${
                                          s.enabled 
                                            ? 'bg-slate-100 text-slate-900 border-slate-200/80 shadow-2xs' 
                                            : 'bg-slate-100 text-slate-400 border-slate-200/50'
                                        }`}
                                      >
                                        {t}
                                      </span>
                                    ))}
                                    {hasMore && (
                                      <span 
                                        className={`px-1.5 py-0.5 rounded-md text-xs font-semibold tracking-normal border cursor-default select-none ${
                                          s.enabled 
                                            ? 'bg-slate-100 text-slate-900 border-slate-200/80 shadow-2xs' 
                                            : 'bg-slate-100 text-slate-400 border-slate-200/50'
                                        }`}
                                        title={`Semua jam siar: ${allTimes.join(', ')}`}
                                      >
                                        ...
                                      </span>
                                    )}
                                  </div>
                                );
                              })()}
                            </td>

                            {/* Nama Jadwal & Audio & Target */}
                            <td className="py-3 px-4 min-w-0 max-w-[320px] lg:max-w-[420px]">
                              <div 
                                className={`font-semibold text-sm leading-snug truncate ${
                                  s.enabled ? 'text-slate-900' : 'text-slate-500'
                                }`}
                                title={s.name}
                              >
                                {s.name}
                              </div>
                              <div className="flex items-center gap-1.5 text-[11px] text-slate-500 mt-1 min-w-0">
                                <div 
                                  className="flex items-center gap-1 min-w-0 max-w-[150px] sm:max-w-[200px] md:max-w-[260px] truncate"
                                  title={s.audio_title || 'Audio default'}
                                >
                                  <Music className="w-3 h-3 text-blue-500 shrink-0" />
                                  <span className="truncate">{s.audio_title || 'Audio default'}</span>
                                </div>
                                <span className="text-slate-300 shrink-0">•</span>
                                {(() => {
                                  const targetText = getScheduleTargetBadge(s);
                                  return (
                                    <span 
                                      className="inline-flex items-center text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200/60 min-w-0 max-w-[130px] sm:max-w-[180px] shrink-0"
                                      title={targetText}
                                    >
                                      <span className="truncate">{targetText}</span>
                                    </span>
                                  );
                                })()}
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

                                {/* Tes Bunyikan Jadwal Ini (Sesuai Target Jadwal) */}
                                <button 
                                  onClick={() => handleTriggerSchedule(s)}
                                  disabled={triggeringScheduleId === s.id}
                                  title={`Uji siarkan jadwal "${s.name}" sekarang (ke target: ${getScheduleTargetBadge(s)})`}
                                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                                    triggeringScheduleId === s.id
                                      ? 'bg-blue-100 text-blue-700 animate-pulse'
                                      : 'text-slate-400 hover:text-blue-600 hover:bg-slate-100'
                                  }`}
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
              <div className="flex items-center gap-1.5 flex-wrap">
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
                  Semua • {audioList.length}
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
                  <span>Rutin • {audioList.filter(a => (a.category || 'biasa') === 'biasa').length}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setAudioCategoryFilter('safety')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    audioCategoryFilter === 'safety'
                      ? 'bg-amber-600 text-white shadow-2xs'
                      : 'bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200/80'
                  }`}
                >
                  <HardHat className="w-3 h-3 text-amber-600" />
                  <span>K3 & Safety • {audioList.filter(a => a.category === 'safety').length}</span>
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
                  <span>Darurat • {emergencyAudios.length}</span>
                </button>
              </div>

              <div className="text-[11px] text-slate-400">
                Pilih ikon pensil di kolom aksi untuk mengubah prioritas atau nama audio.
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
                        const isSafety = (a.category || '').toLowerCase() === 'safety';
                        return (
                          <tr 
                            key={a.id} 
                            className={`transition-colors ${
                              isDarurat ? 'bg-rose-50/25 hover:bg-rose-50/50' : isSafety ? 'bg-amber-50/25 hover:bg-amber-50/50' : 'hover:bg-slate-50/80'
                            }`}
                          >
                            <td className="py-3 px-4 whitespace-nowrap">
                              <span className={`w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-semibold ${
                                isDarurat ? 'bg-rose-100 text-rose-700' : isSafety ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700'
                              }`}>
                                {a.format}
                              </span>
                            </td>

                            {/* Prioritas / Kategori */}
                            <td className="py-3 px-4 whitespace-nowrap">
                              <button
                                type="button"
                                onClick={(e) => handleCycleCategory(a, e)}
                                className="cursor-pointer transition-transform active:scale-95 text-left group/badge"
                                title="Klik untuk beralih prioritas: Rutin → K3 & Safety → Darurat"
                              >
                                {isDarurat ? (
                                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-rose-100/80 hover:bg-rose-100 text-rose-700 border border-rose-200 shadow-2xs group-hover/badge:ring-1 group-hover/badge:ring-rose-300">
                                    <Siren className="w-3.5 h-3.5 text-rose-600 animate-pulse" />
                                    <span>Darurat</span>
                                  </span>
                                ) : isSafety ? (
                                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-amber-100/80 hover:bg-amber-100 text-amber-800 border border-amber-200 shadow-2xs group-hover/badge:ring-1 group-hover/badge:ring-amber-300">
                                    <HardHat className="w-3.5 h-3.5 text-amber-600" />
                                    <span>K3 & Safety</span>
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 group-hover/badge:ring-1 group-hover/badge:ring-slate-300">
                                    <Volume2 className="w-3.5 h-3.5 text-slate-400" />
                                    <span>Rutin</span>
                                  </span>
                                )}
                              </button>
                            </td>

                            <td className="py-3 px-4 min-w-0">
                              <div className={`font-semibold truncate flex items-center gap-1.5 ${
                                isDarurat ? 'text-rose-950 font-bold' : isSafety ? 'text-amber-950 font-semibold' : 'text-slate-900'
                              }`}>
                                {isDarurat && <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />}
                                {isSafety && <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />}
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
                                  onClick={() => setPlayConfirmAudio(a)}
                                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                                    isDarurat 
                                      ? 'text-rose-600 hover:bg-rose-100/70 hover:text-rose-700' 
                                      : isSafety
                                        ? 'text-amber-600 hover:bg-amber-100/70 hover:text-amber-700'
                                        : 'text-slate-400 hover:text-blue-600 hover:bg-slate-100'
                                  }`}
                                  title="Siarkan ke speaker luar"
                                >
                                  <Play className="w-3.5 h-3.5 fill-current" />
                                </button>

                                {/* Ubah Prioritas / Edit */}
                                <button 
                                  onClick={() => handleRequestChangeCategory(a, a.category || 'biasa')}
                                  className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors cursor-pointer"
                                  title="Ubah prioritas atau nama audio"
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
                              <span>{isOnline ? (s.device_type === 'node' ? 'Online DHCP' : `${s.latency_ms || 1}ms`) : 'Offline'}</span>
                            </span>
                          </td>
                          <td className="py-2 px-3 font-semibold text-slate-900 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              {s.device_type === 'node' ? (
                                <span className="p-1 rounded bg-indigo-50 text-indigo-600 shrink-0" title="PC Audio Node Windows">
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
                  <span className="text-[11px] text-slate-400">Pilih satu atau beberapa group</span>
                </div>
                <input 
                  type="text" 
                  required
                  placeholder="Ketik nama group, pisahkan koma untuk beberapa group: Kantor, Satpam"
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
                  disabled={isSavingSpeaker}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white shadow-xs disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isSavingSpeaker ? 'Menyimpan...' : (editingSpeaker ? 'Simpan' : 'Tambahkan')}
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
                  Sirine peringatan darurat akan langsung dibunyikan ke speaker fisik luar. Pastikan kondisi darurat atau telah dikoordinasikan.
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
                <CustomDropdown
                  value={selectedEmergencyAudio || settings.siren_audio_filename || emergencyAudios[0]?.filename || 'sirine_ews_test.wav'}
                  onChange={val => setSelectedEmergencyAudio(val)}
                  options={emergencyAudios.map(ea => ({
                    value: ea.filename,
                    label: `${ea.display_name} • ${ea.filename}`,
                    icon: <Siren className="w-3.5 h-3.5 text-rose-500" />
                  }))}
                  variant="light"
                  size="sm"
                  buttonClassName="bg-white border-rose-200 text-rose-700 min-w-[200px]"
                />
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
                  const chosenAudio = selectedEmergencyAudio || settings.siren_audio_filename || emergencyAudios[0]?.filename || 'sirine_ews_test.wav';
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
      {/* MODAL: KONFIRMASI SIARAN AUDIO DARI TABEL                */}
      {/* ========================================================= */}
      {playConfirmAudio && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-md p-5 shadow-xl animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-start gap-3.5">
              <div className={`p-2.5 rounded-xl border shrink-0 ${
                playConfirmAudio.category === 'darurat'
                  ? 'bg-rose-50 border-rose-200'
                  : 'bg-blue-50 border-blue-200'
              }`}>
                {playConfirmAudio.category === 'darurat' ? (
                  <Siren className="w-6 h-6 text-rose-600 animate-pulse" />
                ) : (
                  <Radio className="w-6 h-6 text-blue-600" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-slate-900 leading-snug">
                  {playConfirmAudio.category === 'darurat' 
                    ? 'Konfirmasi Siaran Audio Darurat' 
                    : 'Konfirmasi Siaran Audio'}
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  {playConfirmAudio.category === 'darurat'
                    ? 'Peringatan: Berkas audio ini berkategori Darurat dan akan disiarkan ke speaker fisik luar / PC Node.'
                    : 'Audio ini akan disiarkan langsung ke speaker fisik & PC Node sesuai target siaran yang aktif.'}
                </p>
              </div>
              <button 
                onClick={() => setPlayConfirmAudio(null)} 
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4 p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 text-xs space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-500 font-medium shrink-0">Nama Audio:</span>
                <span className="font-semibold text-slate-800 truncate" title={playConfirmAudio.display_name}>
                  {playConfirmAudio.display_name}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-500 font-medium shrink-0">Berkas:</span>
                <span className="text-slate-600 font-mono text-[11px] truncate">
                  {playConfirmAudio.filename} • {formatSec(playConfirmAudio.duration)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-200/60">
                <span className="text-slate-500 font-medium shrink-0">Target Siaran:</span>
                <span className="font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-200/60 truncate max-w-[200px]" title={targetSummaryText}>
                  {targetSummaryText}
                </span>
              </div>
            </div>

            <div className="mt-3 text-[11px] bg-sky-50/70 text-sky-800 border border-sky-200/60 p-2.5 rounded-xl flex items-center gap-2">
              <Headphones className="w-4 h-4 shrink-0 text-sky-600" />
              <span>Ingin mendengar sendiri dulu tanpa siaran ke luar? Gunakan tombol <strong>Headphone</strong> di baris tabel.</span>
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setPlayConfirmAudio(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={() => {
                  const audioId = playConfirmAudio.id;
                  setPlayConfirmAudio(null);
                  handlePlayToSpeakers(audioId);
                }}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white shadow-xs transition-all cursor-pointer ${
                  playConfirmAudio.category === 'darurat'
                    ? 'bg-rose-600 hover:bg-rose-700'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Ya, Siarkan Sekarang</span>
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
                    label: a.category === 'darurat' ? `[Darurat] ${a.display_name}` : a.category === 'safety' ? `[K3] ${a.display_name}` : a.display_name,
                    sublabel: `${a.category === 'darurat' ? 'Darurat' : a.category === 'safety' ? 'K3 & Safety' : 'Rutin'} • ${a.filename} • ${formatSec(a.duration)}`
                  }))}
                  variant="light"
                  className="w-full"
                  buttonClassName="w-full bg-white justify-between"
                  placeholder="Pilih berkas audio..."
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Target Siaran</label>
                <MultiTargetSelector
                  targetMode={newSchedule.target_mode || 'all'}
                  selectedGroups={newSchedule.target_group ? newSchedule.target_group.split(',').map(s => s.trim()).filter(Boolean) : []}
                  selectedSpeakerIds={newSchedule.target_speakers ? newSchedule.target_speakers.split(',').map(s => parseInt(s.trim(), 10)).filter(Boolean) : (newSchedule.target_speaker_id ? [newSchedule.target_speaker_id] : [])}
                  onChange={({ targetMode: tm, selectedGroups: sg, selectedSpeakerIds: spids }) => {
                    setNewSchedule(prev => ({
                      ...prev,
                      target_mode: tm,
                      target_group: sg.join(', '),
                      target_zone: sg.join(', '),
                      target_speakers: spids.join(', '),
                      target_speaker_id: spids[0] || 0
                    }));
                  }}
                  speakers={speakers}
                  groupsList={groupsList}
                  variant="light"
                  size="md"
                  align="left"
                  buttonClassName="w-full bg-white justify-between"
                  className="w-full"
                />
              </div>

              {/* Multi-Time Picker */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-blue-600" />
                    <span>Waktu Siar</span>
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
                        className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-lg bg-white border border-blue-200/80 text-blue-700 text-xs font-semibold shadow-2xs"
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
                    { value: 'daily', label: 'Setiap hari • Senin sampai Minggu' },
                    { value: 'weekdays', label: 'Hari kerja • Senin sampai Jumat' },
                    { value: 'custom', label: 'Pilih hari tertentu' },
                    { value: 'once', label: 'Sekali siar' }
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
                  disabled={isSavingSchedule}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white shadow-xs disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isSavingSchedule ? 'Menyimpan...' : 'Simpan Jadwal'}
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
                  : categoryChangeTarget.targetCategory === 'safety'
                    ? 'bg-amber-50 border-amber-200 text-amber-700'
                    : 'bg-blue-50 border-blue-200 text-blue-600'
              }`}>
                {categoryChangeTarget.targetCategory === 'darurat' ? (
                  <Siren className="w-6 h-6 animate-pulse" />
                ) : categoryChangeTarget.targetCategory === 'safety' ? (
                  <HardHat className="w-6 h-6" />
                ) : (
                  <Volume2 className="w-6 h-6" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-slate-900 leading-snug">
                  Ubah Prioritas Audio
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  {categoryChangeTarget.targetCategory === 'darurat'
                    ? 'Prioritas 1: Sirine bahaya, alarm evakuasi, dan peringatan darurat.'
                    : categoryChangeTarget.targetCategory === 'safety'
                      ? 'Prioritas 2: Pengumuman K3, briefing keselamatan kerja, dan instruksi APD.'
                      : 'Prioritas 3: Siaran operasional reguler dan pengumuman rutin harian.'}
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
                <label className="block text-[11px] font-semibold text-slate-500 mb-1">Nama Tampilan Audio</label>
                <input
                  type="text"
                  value={editingDisplayName}
                  onChange={e => setEditingDisplayName(e.target.value)}
                  placeholder="Ketik nama tampilan audio..."
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-900 focus:ring-2 focus:ring-blue-500 outline-hidden font-medium"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-500 mb-1.5">Pilih Kondisi atau Prioritas:</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setCategoryChangeTarget(prev => ({ ...prev, targetCategory: 'biasa' }))}
                    className={`p-2 rounded-xl border text-left transition-all cursor-pointer ${
                      categoryChangeTarget.targetCategory === 'biasa'
                        ? 'bg-blue-50/90 border-blue-500 text-blue-900 shadow-2xs font-semibold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 text-xs font-semibold">
                      <Volume2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span>Rutin</span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">Prioritas 3</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setCategoryChangeTarget(prev => ({ ...prev, targetCategory: 'safety' }))}
                    className={`p-2 rounded-xl border text-left transition-all cursor-pointer ${
                      categoryChangeTarget.targetCategory === 'safety'
                        ? 'bg-amber-50/90 border-amber-500 text-amber-900 shadow-2xs font-semibold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-800">
                      <HardHat className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                      <span>K3 Safety</span>
                    </div>
                    <div className="text-[10px] text-amber-600/70 mt-1">Prioritas 2</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setCategoryChangeTarget(prev => ({ ...prev, targetCategory: 'darurat' }))}
                    className={`p-2 rounded-xl border text-left transition-all cursor-pointer ${
                      categoryChangeTarget.targetCategory === 'darurat'
                        ? 'bg-rose-50 border-rose-500 text-rose-900 shadow-2xs font-semibold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-600">
                      <Siren className="w-3.5 h-3.5 shrink-0" />
                      <span>Darurat</span>
                    </div>
                    <div className="text-[10px] text-rose-500/70 mt-1">Prioritas 1</div>
                  </button>
                </div>
              </div>

              <div className="pt-1 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
                <span>Nama berkas fisik:</span>
                <span className="font-medium text-slate-700 truncate max-w-[200px]">{categoryChangeTarget.audio.filename}</span>
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
                    : categoryChangeTarget.targetCategory === 'safety'
                      ? 'bg-amber-600 hover:bg-amber-700'
                      : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                <Check className="w-3.5 h-3.5" />
                <span>Simpan Perubahan</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: UNGGAH BERKAS AUDIO                                */}
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
                  <p className="text-xs text-slate-500">Pilih berkas dan tentukan tingkat prioritas siaran</p>
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
                    <p className="text-xs font-semibold text-slate-700">Pilih berkas suara dari komputer</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">Format didukung: MP3, WAV, OGG, FLAC</p>
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
                  placeholder="Contoh: Apel Pagi, Pengingat APD, Sirine Gempa"
                  value={uploadDisplayName}
                  onChange={e => setUploadDisplayName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                />
              </div>

              {/* Pilihan Kondisi / Kategori Suara */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-slate-700">
                    Kategori dan Tingkat Prioritas
                  </label>
                  <span className="text-[11px] text-slate-400">Pilih salah satu tingkatan</span>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  {/* Opsi 1: Rutin */}
                  <div
                    onClick={() => setUploadCategory('biasa')}
                    className={`p-2.5 rounded-xl border-2 cursor-pointer transition-all ${
                      uploadCategory === 'biasa'
                        ? 'border-blue-500 bg-blue-50/60 shadow-2xs'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-semibold text-xs text-slate-900 mb-1">
                      <Volume2 className="w-4 h-4 text-blue-600 shrink-0" />
                      <span>Rutin</span>
                    </div>
                    <div className="text-[10px] font-semibold text-blue-600 mb-1">Prioritas 3</div>
                    <p className="text-[10px] text-slate-500 leading-tight">
                      Pengumuman umum, bel pergantian, apel pagi, informasi reguler.
                    </p>
                  </div>

                  {/* Opsi 2: K3 & Safety */}
                  <div
                    onClick={() => setUploadCategory('safety')}
                    className={`p-2.5 rounded-xl border-2 cursor-pointer transition-all ${
                      uploadCategory === 'safety'
                        ? 'border-amber-500 bg-amber-50/70 shadow-2xs'
                        : 'border-slate-200 bg-white hover:bg-amber-50/20'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-semibold text-xs text-amber-900 mb-1">
                      <HardHat className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>K3 & Safety</span>
                    </div>
                    <div className="text-[10px] font-semibold text-amber-600 mb-1">Prioritas 2</div>
                    <p className="text-[10px] text-amber-700/80 leading-tight">
                      Briefing K3, pengingat keselamatan, pemakaian APD lapangan.
                    </p>
                  </div>

                  {/* Opsi 3: Darurat */}
                  <div
                    onClick={() => setUploadCategory('darurat')}
                    className={`p-2.5 rounded-xl border-2 cursor-pointer transition-all ${
                      uploadCategory === 'darurat'
                        ? 'border-rose-500 bg-rose-50/70 shadow-2xs'
                        : 'border-slate-200 bg-white hover:bg-rose-50/20'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-semibold text-xs text-rose-700 mb-1">
                      <Siren className="w-4 h-4 text-rose-600 shrink-0 animate-pulse" />
                      <span>Darurat</span>
                    </div>
                    <div className="text-[10px] font-semibold text-rose-600 mb-1">Prioritas 1</div>
                    <p className="text-[10px] text-rose-600/80 leading-tight">
                      Sirine bahaya, alarm evakuasi, gempa, kebakaran, darurat.
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
                      : uploadCategory === 'safety'
                        ? 'bg-amber-600 hover:bg-amber-700'
                        : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>
                    {isUploading 
                      ? 'Mengunggah...' 
                      : uploadCategory === 'darurat' 
                        ? 'Unggah Suara Darurat' 
                        : uploadCategory === 'safety' 
                          ? 'Unggah Suara K3' 
                          : 'Unggah Suara Rutin'}
                  </span>
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
                placeholder="Nama group baru... contoh: Workshop, Dermaga 2"
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
      {/* MODAL: PENGATURAN SISTEM & TOMBOL CEPAT                   */}
      {/* ========================================================= */}
      {showSettings && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-md p-5 shadow-xl">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                  <Settings className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900">Pengaturan Sistem</h3>
                  <p className="text-[11px] text-slate-500">Sesuaikan audio tombol cepat dan jaringan</p>
                </div>
              </div>
              <button 
                onClick={() => setShowSettings(false)} 
                className="text-slate-400 hover:text-slate-600 cursor-pointer p-1 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-4.5 h-4.5" />
              </button>
            </div>

            <form onSubmit={handleSaveSettings} className="space-y-4">
              {/* Seksi Tombol Cepat */}
              <div>
                <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                  Audio Tombol Cepat
                </label>
                <div className="space-y-3 p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                  {/* Pilihan Audio Sirine */}
                  <div>
                    <div className="flex items-center gap-1.5 mb-1.5 text-xs font-medium text-slate-700">
                      <Siren className="w-3.5 h-3.5 text-rose-500" />
                      <span>Audio Tombol Sirine:</span>
                    </div>
                    <CustomDropdown
                      value={settings.siren_audio_filename || 'sirine_ews_test.wav'}
                      onChange={val => setSettings({ ...settings, siren_audio_filename: val })}
                      options={audioList.map(a => ({
                        value: a.filename,
                        label: a.display_name,
                        sublabel: `${a.category === 'darurat' ? 'Darurat' : a.category === 'safety' ? 'K3 & Safety' : 'Rutin'} • ${a.filename}`,
                        icon: a.category === 'darurat' ? <Siren className="w-3.5 h-3.5 text-rose-500" /> : a.category === 'safety' ? <HardHat className="w-3.5 h-3.5 text-amber-500" /> : <Music className="w-3.5 h-3.5 text-slate-400" />
                      }))}
                      variant="light"
                      className="w-full"
                      buttonClassName="w-full bg-white justify-between"
                    />
                  </div>

                  {/* Pilihan Audio K3 */}
                  <div>
                    <div className="flex items-center gap-1.5 mb-1.5 text-xs font-medium text-slate-700">
                      <HardHat className="w-3.5 h-3.5 text-emerald-500" />
                      <span>Audio Tombol K3:</span>
                    </div>
                    <CustomDropdown
                      value={settings.k3_audio_filename || 'safety_k3_chime.wav'}
                      onChange={val => setSettings({ ...settings, k3_audio_filename: val })}
                      options={audioList.map(a => ({
                        value: a.filename,
                        label: a.display_name,
                        sublabel: `${a.category === 'darurat' ? 'Darurat' : a.category === 'safety' ? 'K3 & Safety' : 'Rutin'} • ${a.filename}`,
                        icon: <HardHat className="w-3.5 h-3.5 text-emerald-500" />
                      }))}
                      variant="light"
                      className="w-full"
                      buttonClassName="w-full bg-white justify-between"
                    />
                  </div>
                </div>
              </div>

              {/* Seksi Jaringan Multicast */}
              <div>
                <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                  Jaringan Multicast Speaker Fisik
                </label>
                <div className="space-y-2.5 p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-600 mb-1">Alamat IP Multicast</label>
                    <input 
                      type="text" 
                      value={settings.multicast_ip || ''}
                      onChange={e => setSettings({ ...settings, multicast_ip: e.target.value })}
                      className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-slate-600 mb-1">Port UDP Multicast</label>
                    <input 
                      type="text" 
                      value={settings.multicast_port || ''}
                      onChange={e => setSettings({ ...settings, multicast_port: e.target.value })}
                      className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs focus:ring-2 focus:ring-blue-500 outline-hidden"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2 border-t border-slate-100">
                <button 
                  type="button" 
                  onClick={() => setShowSettings(false)}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100 cursor-pointer"
                >
                  Batal
                </button>
                <button 
                  type="submit" 
                  className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-xs cursor-pointer"
                >
                  Simpan Pengaturan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
