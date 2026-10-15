import { useState, useRef, useEffect, useCallback } from 'react';
import { Sparkles, RotateCcw, Bot, Send, Loader2, Zap, Clock, ChevronDown, GripVertical } from 'lucide-react';
import { streamChatMessage } from '../api/chat';
import { useVideo } from '../context/VideoContext';
import MarkdownRenderer from './MarkdownRenderer';

const MIN_WIDTH = 280;
const MAX_WIDTH = 600;
const DEFAULT_WIDTH = 360;

function buildInitialMessages(videoId) {
    const isDemoVideo = String(videoId || '').startsWith('demo-');
    if (!isDemoVideo) {
        return [
            {
                id: 'welcome',
                type: 'bot',
                text: '영상에 대해 궁금한 점을 물어보세요!',
                timestamp: 'Now',
            },
        ];
    }

    return [
        {
            id: 'welcome',
            type: 'bot',
            text: '영상에 대해 궁금한 점을 물어보세요. 시간 구간과 화면 근거를 기준으로 답변합니다.',
            timestamp: 'Now',
            suggestions: [],
        },
    ];
}

function buildDemoAnswer(question) {
    const text = String(question || '').trim();
    if (text.includes('검색') || text.includes('치환') || text.includes('어느 구간')) {
        return {
            answer: '관련 내용은 **02:10-04:20** 구간에서 확인할 수 있습니다. 이 구간은 STT 설명뿐 아니라 화면에 보이는 편집기 UI와 코드 조각을 함께 근거로 봐야 기능의 사용 흐름을 이해하기 쉽습니다.',
            suggestions: [],
        };
    }
    if (text.includes('근거') || text.includes('추적') || text.includes('시간')) {
        return {
            answer: 'SeSAC:Note는 답변에 사용한 요약 세그먼트와 `source_refs`를 함께 저장합니다. 예를 들어 이 답변은 **Segment 2 (02:10-04:20)**의 음성 설명과 화면 캡처 근거를 참조한 것으로 표시할 수 있습니다.',
            suggestions: [],
        };
    }
    if (text.includes('핵심') || text.includes('정리')) {
        return {
            answer: '핵심은 세 가지입니다. 첫째, Kate 편집기에서 반복 작업을 줄이는 편집 기능을 소개합니다. 둘째, 검색/치환과 줄 편집처럼 화면 조작을 함께 봐야 이해되는 기능이 많습니다. 셋째, SeSAC:Note는 이런 화면·시간 정보를 구간별 근거로 묶어 AI 노트와 QA에 연결합니다.',
            suggestions: [],
        };
    }
    return {
        answer: 'Kate 텍스트 편집기의 생산성 팁을 실제 화면 조작과 함께 보여주는 영상입니다. 초반에는 편집기 화면과 예제 파일을 소개하고, 중반 이후에는 검색/치환, 줄 편집, 파일 이동 같은 반복 작업을 줄이는 기능을 설명합니다.',
        suggestions: [],
    };
}

function ChatBot({ videoId }) {
    const { chatSessionId, setChatSessionId } = useVideo();
    const [width, setWidth] = useState(DEFAULT_WIDTH);
    const [isResizing, setIsResizing] = useState(false);
    const resizeRef = useRef(null);
    const [messages, setMessages] = useState(() => buildInitialMessages(videoId));
    const [inputValue, setInputValue] = useState('');
    const [sending, setSending] = useState(false);
    const [reasoningMode, setReasoningMode] = useState('flash'); // 'flash' or 'thinking'
    const [modeMenuOpen, setModeMenuOpen] = useState(false);
    const messagesContainerRef = useRef(null);
    const abortRef = useRef(null);
    const modeMenuRef = useRef(null);
    const textareaRef = useRef(null);
    const messageCounterRef = useRef(0);

    const nextMessageId = (prefix) => {
        messageCounterRef.current += 1;
        return `${prefix}-${messageCounterRef.current}`;
    };

    const streamDemoAnswer = ({ botId, answer, suggestions }) => {
        const initialDelayMs = 320;
        const chunkSize = 7;
        const chunkDelayMs = 18;
        const timers = [];

        const startTimer = setTimeout(() => {
            let cursor = 0;
            const interval = setInterval(() => {
                cursor = Math.min(cursor + chunkSize, answer.length);
                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === botId
                            ? {
                                ...msg,
                                text: answer.slice(0, cursor),
                                streaming: cursor < answer.length,
                                suggestions: cursor >= answer.length ? suggestions : [],
                            }
                            : msg
                    )
                );

                if (cursor >= answer.length) {
                    clearInterval(interval);
                    setSending(false);
                    abortRef.current = null;
                }
            }, chunkDelayMs);
            timers.push(interval);
        }, initialDelayMs);
        timers.push(startTimer);

        abortRef.current = {
            abort: () => {
                timers.forEach((timer) => clearTimeout(timer));
                timers.forEach((timer) => clearInterval(timer));
                setSending(false);
            },
        };
    };

    // Auto-resize textarea
    const adjustTextareaHeight = () => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            const maxHeight = 140; // ~5 lines
            const newHeight = Math.min(textarea.scrollHeight, maxHeight);
            textarea.style.height = `${newHeight}px`;
            // Only show scrollbar when content exceeds maxHeight
            textarea.style.overflowY = textarea.scrollHeight > maxHeight ? 'auto' : 'hidden';
        }
    };

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (modeMenuRef.current && !modeMenuRef.current.contains(e.target)) {
                setModeMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Resize handlers
    const handleMouseDown = useCallback((e) => {
        e.preventDefault();
        setIsResizing(true);
        resizeRef.current = {
            startX: e.clientX,
            startWidth: width,
        };
    }, [width]);

    useEffect(() => {
        const handleMouseMove = (e) => {
            if (!isResizing || !resizeRef.current) return;
            const delta = resizeRef.current.startX - e.clientX;
            const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, resizeRef.current.startWidth + delta));
            setWidth(newWidth);
        };

        const handleMouseUp = () => {
            setIsResizing(false);
            resizeRef.current = null;
        };

        if (isResizing) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        }

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
    }, [isResizing]);

    useEffect(() => {
        const container = messagesContainerRef.current;
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }, [messages]);

    useEffect(() => {
        return () => {
            abortRef.current?.abort();
        };
    }, []);

    useEffect(() => {
        abortRef.current?.abort();
        abortRef.current = null;
        setSending(false);
        setMessages(buildInitialMessages(videoId));
        setChatSessionId(null);
        messageCounterRef.current = 0;
    }, [videoId, setChatSessionId]);

    const handleSend = async (presetText = null) => {
        const text = (typeof presetText === 'string' ? presetText : inputValue).trim();
        if (!text || sending) return;

        const botId = nextMessageId('bot');
        const userMsg = {
            id: nextMessageId('user'),
            type: 'user',
            text,
            timestamp: 'Now',
        };
        const botMsg = {
            id: botId,
            type: 'bot',
            text: '',
            timestamp: 'Now',
            streaming: true,
            suggestions: [],
            messageId: null,
        };
        setMessages((prev) => [...prev, userMsg, botMsg]);
        setInputValue('');
        setSending(true);
        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }

        if (String(videoId || '').startsWith('demo-')) {
            const { answer, suggestions } = buildDemoAnswer(text);
            streamDemoAnswer({ botId, answer, suggestions });
            return;
        }

        abortRef.current = streamChatMessage({
            videoId: videoId || '',
            message: text,
            sessionId: chatSessionId,
            reasoningMode: reasoningMode,
            onSessionId: (sessionId) => {
                if (sessionId) setChatSessionId(sessionId);
            },
            onChunk: (chunk, isFinal, payload) => {
                if (!chunk && !isFinal) return;
                setMessages((prev) =>
                    prev.map((msg) => {
                        if (msg.id !== botId) return msg;
                        const nextText = `${msg.text || ''}${chunk || ''}`;
                        return {
                            ...msg,
                            text: nextText,
                            streaming: !isFinal,
                            messageId: payload?.message_id || msg.messageId || null,
                        };
                    })
                );
                if (isFinal) {
                    setSending(false);
                }
            },
            onSuggestions: (payload) => {
                const questions = Array.isArray(payload?.questions)
                    ? payload.questions
                        .map((item) => String(item || '').trim())
                        .filter(Boolean)
                        .slice(0, 2)
                    : [];
                if (!questions.length) return;
                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === botId
                            ? {
                                ...msg,
                                suggestions: questions,
                                messageId: payload?.message_id || msg.messageId || null,
                            }
                            : msg
                    )
                );
            },
            onDone: () => {
                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === botId ? { ...msg, streaming: false } : msg
                    )
                );
                setSending(false);
                abortRef.current = null;
            },
            onError: (err) => {
                setMessages((prev) => {
                    const next = prev.map((msg) =>
                        msg.id === botId ? { ...msg, streaming: false } : msg
                    );
                    next.push({
                        id: nextMessageId('err'),
                        type: 'bot',
                        text: `오류가 발생했습니다: ${err.message || 'Unknown error'}`,
                        timestamp: 'Now',
                    });
                    return next;
                });
                setSending(false);
                abortRef.current = null;
            },
        });
    };

    const handleSuggestionClick = (question) => {
        if (!question || sending) return;
        handleSend(question);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleClear = () => {
        abortRef.current?.abort();
        abortRef.current = null;
        setSending(false);
        setMessages([
            ...buildInitialMessages(videoId),
        ]);
        setChatSessionId(null);
    };

    return (
        <aside
            className="hidden lg:flex flex-col border-l border-[var(--border-color)] bg-surface shrink-0 h-full overflow-hidden relative"
            style={{ width: `${width}px` }}
        >
            {/* Resize Handle */}
            <div
                onMouseDown={handleMouseDown}
                className={`absolute left-0 top-0 bottom-0 w-1 cursor-col-resize z-20 group flex items-center justify-center hover:bg-primary/30 transition-colors ${isResizing ? 'bg-primary/40' : ''}`}
            >
                <div className={`absolute left-0 w-3 h-full`} /> {/* Larger hit area */}
                <div className={`opacity-0 group-hover:opacity-100 transition-opacity ${isResizing ? 'opacity-100' : ''}`}>
                    <GripVertical className="w-3 h-3 text-primary" />
                </div>
            </div>
            {/* Chat Header */}
            <div className="p-4 border-b border-[var(--border-color)] bg-surface z-10 shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-primary" />
                    <h3 className="text-[var(--text-primary)] font-medium text-sm">Ask SeSAC:Note AI</h3>
                </div>
                <button
                    onClick={handleClear}
                    className="text-gray-400 hover:text-[var(--text-primary)]"
                    title="Clear History"
                >
                    <RotateCcw className="w-[18px] h-[18px]" />
                </button>
            </div>

            {/* Messages Container */}
            <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 custom-scrollbar">
                {messages.map((msg) => (
                    <div key={msg.id} className={`flex gap-3 ${msg.type === 'user' ? 'flex-row-reverse' : ''}`}>
                        {msg.type === 'bot' ? (
                            <div className="size-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0 border border-primary/20">
                                <Bot className="w-4 h-4 text-primary" />
                            </div>
                        ) : (
                            <div className="size-8 rounded-full bg-gray-700 flex items-center justify-center shrink-0 text-white text-xs font-bold">
                                U
                            </div>
                        )}

                        <div className={`flex flex-col gap-1 ${msg.type === 'user' ? 'items-end' : ''} max-w-[85%]`}>
                            <div className={`${msg.type === 'bot' ? 'bg-surface-highlight rounded-tl-none border border-[var(--border-color)] text-[var(--text-secondary)]' : 'bg-primary rounded-tr-none text-white'} p-3 rounded-2xl text-sm leading-relaxed shadow-sm`}>
                                {msg.type === 'bot' ? (
                                    <div className="chat-markdown overflow-hidden">
                                        <MarkdownRenderer>{msg.text}</MarkdownRenderer>
                                        {msg.streaming && (
                                            msg.text ? (
                                                <span className="inline-block w-2 h-4 bg-primary/70 animate-pulse align-middle ml-1 rounded-sm" />
                                            ) : (
                                                <Loader2 className="w-4 h-4 animate-spin text-primary inline-block" />
                                            )
                                        )}
                                    </div>
                                ) : (
                                    <p className="whitespace-pre-wrap">{msg.text}</p>
                                )}
                            </div>
                            {msg.type === 'bot' && !msg.streaming && Array.isArray(msg.suggestions) && msg.suggestions.length > 0 && (
                                <div className="flex flex-wrap gap-2 pl-1">
                                    {msg.suggestions.map((question, index) => (
                                        <button
                                            key={`${msg.id}-suggestion-${index}`}
                                            type="button"
                                            onClick={() => handleSuggestionClick(question)}
                                            disabled={sending}
                                            className="px-3.5 py-2 rounded-lg border-2 border-[var(--chip-suggestion-border)] bg-[var(--chip-suggestion-bg)] text-[13px] leading-snug text-[var(--chip-suggestion-text)] font-medium shadow-sm hover:bg-[var(--chip-suggestion-hover-bg)] hover:border-[var(--chip-suggestion-hover-border)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {question}
                                        </button>
                                    ))}
                                </div>
                            )}
                            <span className={`text-[10px] text-gray-500 ${msg.type === 'user' ? 'pr-1' : 'pl-1'}`}>{msg.timestamp}</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-[var(--border-color)] bg-surface/95 backdrop-blur">
                <div className="bg-surface-highlight rounded-xl">
                    {/* Textarea */}
                    <textarea
                        ref={textareaRef}
                        className="w-full bg-transparent border-0 px-4 pt-3 pb-0 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-0 placeholder:text-gray-500 resize-none [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-gray-400/50 [&::-webkit-scrollbar-thumb]:rounded-full"
                        placeholder="Ask a question..."
                        rows={1}
                        value={inputValue}
                        onChange={(e) => {
                            setInputValue(e.target.value);
                            adjustTextareaHeight();
                        }}
                        onKeyDown={handleKeyDown}
                        disabled={sending}
                        style={{ minHeight: '24px', maxHeight: '140px', overflowY: 'hidden' }}
                    />
                    {/* Bottom row: Mode selector + Send button */}
                    <div className="flex items-center justify-between px-2 pb-2">
                        {/* Mode Selector */}
                        <div className="relative" ref={modeMenuRef}>
                            <button
                                onClick={() => setModeMenuOpen(!modeMenuOpen)}
                                disabled={sending}
                                className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-surface transition-all disabled:opacity-50 text-xs"
                                title={reasoningMode === 'flash' ? '요약 기반 답변' : '원본 분석 답변'}
                            >
                                {reasoningMode === 'flash' ? (
                                    <Zap className="w-3.5 h-3.5 text-yellow-500" />
                                ) : (
                                    <Clock className="w-3.5 h-3.5 text-blue-500" />
                                )}
                                <span className="font-medium">{reasoningMode === 'flash' ? 'Flash' : 'Thinking'}</span>
                                <ChevronDown className={`w-3 h-3 transition-transform ${modeMenuOpen ? 'rotate-180' : ''}`} />
                            </button>
                            {/* Dropdown Menu (opens upward) */}
                            {modeMenuOpen && (
                                <div className="absolute bottom-full left-0 mb-2 w-52 bg-surface border border-[var(--border-color)] rounded-xl shadow-xl overflow-hidden z-50">
                                    <button
                                        onClick={() => {
                                            setReasoningMode('flash');
                                            setModeMenuOpen(false);
                                        }}
                                        className={`w-full flex items-start gap-3 px-3 py-3 text-left hover:bg-surface-highlight transition-colors ${
                                            reasoningMode === 'flash' ? 'bg-primary/10' : ''
                                        }`}
                                    >
                                        <Zap className={`w-4 h-4 mt-0.5 shrink-0 ${reasoningMode === 'flash' ? 'text-yellow-500' : 'text-gray-400'}`} />
                                        <div>
                                            <div className={`text-sm font-medium ${reasoningMode === 'flash' ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>
                                                Flash
                                            </div>
                                            <div className="text-[11px] text-gray-500 mt-0.5">
                                                요약 기반 빠른 답변
                                            </div>
                                        </div>
                                    </button>
                                    <button
                                        onClick={() => {
                                            setReasoningMode('thinking');
                                            setModeMenuOpen(false);
                                        }}
                                        className={`w-full flex items-start gap-3 px-3 py-3 text-left hover:bg-surface-highlight transition-colors ${
                                            reasoningMode === 'thinking' ? 'bg-primary/10' : ''
                                        }`}
                                    >
                                        <Clock className={`w-4 h-4 mt-0.5 shrink-0 ${reasoningMode === 'thinking' ? 'text-blue-500' : 'text-gray-400'}`} />
                                        <div>
                                            <div className={`text-sm font-medium ${reasoningMode === 'thinking' ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>
                                                Thinking
                                            </div>
                                            <div className="text-[11px] text-gray-500 mt-0.5">
                                                원본 분석 심층 답변
                                            </div>
                                        </div>
                                    </button>
                                </div>
                            )}
                        </div>
                        {/* Send Button */}
                        <button
                            onClick={handleSend}
                            disabled={sending || !inputValue.trim()}
                            className="p-2 bg-primary hover:bg-[var(--accent-coral-dark)] rounded-lg text-white transition-colors shadow-sm disabled:opacity-50"
                        >
                            <Send className="w-4 h-4" />
                        </button>
                    </div>
                </div>
                <p className="text-[10px] text-center text-gray-600 mt-2">AI can make mistakes. Check important info.</p>
            </div>
        </aside>
    );
}

export default ChatBot;
