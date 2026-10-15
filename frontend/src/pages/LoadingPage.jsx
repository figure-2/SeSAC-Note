import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';
import { useVideo } from '../context/VideoContext';
import useVideoStatusStream from '../hooks/useVideoStatusStream';
import './LoadingPage.css';

const STAGES = [
    { name: '영상 업로드 완료', Icon: Upload },
    { name: 'STT·화면 추출 중', Icon: RefreshCw },
    { name: 'VLM 화면 분석 중', Icon: RefreshCw },
    { name: 'AI 노트 생성 중', Icon: RefreshCw },
    { name: 'Judge 품질 점검 중', Icon: RefreshCw },
    { name: '분석 완료', Icon: CheckCircle },
];

function statusToStage(videoStatus, processingStatus) {
    const vs = (videoStatus || '').toUpperCase();
    const ps = (processingStatus || '').toUpperCase();
    if (vs === 'FAILED') return -1;
    if (vs === 'DONE' || ps === 'DONE') return 5;
    if (ps === 'JUDGE_RUNNING') return 4;
    if (ps === 'SUMMARY_RUNNING') return 3;
    if (ps === 'VLM_RUNNING') return 2;
    if (vs === 'PREPROCESSING') return 1;
    return 0;
}

function stageToProgress(stage) {
    if (stage <= 0) return 5;
    if (stage === 1) return 20;
    if (stage === 2) return 40;
    if (stage === 3) return 60;
    if (stage === 4) return 80;
    if (stage >= 5) return 100;
}

function LoadingPage() {
    const { currentVideoId } = useVideo();
    const navigate = useNavigate();
    const [stage, setStage] = useState(0);
    const [progress, setProgress] = useState(5);
    const [failed, setFailed] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');
    const [done, setDone] = useState(false);

    // SSE 상태 콜백
    const handleStatus = useCallback((statusData) => {
        if (!statusData) return;
        const vs = (statusData.video_status || '').toUpperCase();

        if (vs === 'FAILED') {
            setFailed(true);
            setErrorMsg(statusData.error_message || '전처리에 실패했습니다.');
            return;
        }

        const ps = statusData.processing_job?.status;
        const s = statusToStage(vs, ps);
        setStage(s);
        const current = statusData.processing_job?.progress_current;
        const total = statusData.processing_job?.progress_total;
        const streamedProgress = total ? Math.round((Number(current || 0) / Number(total)) * 100) : null;
        setProgress(streamedProgress !== null ? Math.max(stageToProgress(s), streamedProgress) : stageToProgress(s));

        // 분석 완료 후 결과 페이지로 이동
        if (vs === 'DONE') {
            setDone(true);
        }
    }, []);

    // SSE 완료 콜백
    const handleDone = useCallback((data) => {
        if (!data) return;
        const vs = (data.video_status || '').toUpperCase();
        if (vs === 'FAILED') {
            setFailed(true);
        } else if (vs === 'DONE') {
            setDone(true);
        }
    }, []);

    // SSE 스트리밍 (polling 대신 사용)
    useVideoStatusStream(currentVideoId, {
        enabled: !!currentVideoId && !failed && !done,
        onStatus: handleStatus,
        onDone: handleDone,
    });

    // 분석 완료 시 분석 결과 페이지로 이동
    useEffect(() => {
        if (done && currentVideoId) {
            const timer = setTimeout(() => navigate(`/analysis/${currentVideoId}`), 300);
            return () => clearTimeout(timer);
        }
    }, [done, currentVideoId, navigate]);

    // videoId 없을 때 (직접 접근) 데모 폴백
    useEffect(() => {
        if (currentVideoId) return;
        const interval = setInterval(() => {
            setProgress((prev) => {
                if (prev >= 100) {
                    clearInterval(interval);
                    return 100;
                }
                return prev + 2;
            });
        }, 100);
        return () => clearInterval(interval);
    }, [currentVideoId]);

    useEffect(() => {
        if (!currentVideoId) {
            if (progress < 40) setStage(0);
            else if (progress < 90) setStage(1);
            else setStage(2);
        }
    }, [progress, currentVideoId]);

    const safeStage = Math.max(0, Math.min(stage, STAGES.length - 1));
    const CurrentIcon = STAGES[safeStage].Icon;

    return (
        <div className="loading-page">
            <div className="loading-card">
                <div className="loading-logo">
                    <span className="logo-re">SeSAC:</span>
                    <span className="logo-view">Note</span>
                </div>

                <div className="page-spinner-wrapper">
                    <div className="spinner"></div>
                </div>

                {failed ? (
                    <div className="loading-stage" style={{ color: '#ef4444' }}>
                        <span className="stage-icon"><AlertCircle className="w-6 h-6" /></span>
                        <span className="stage-name">전처리 실패</span>
                        <p style={{ fontSize: '0.875rem', marginTop: '0.5rem', opacity: 0.8 }}>{errorMsg}</p>
                        <button
                            onClick={() => navigate('/')}
                            style={{
                                marginTop: '1rem',
                                padding: '0.5rem 1.5rem',
                                borderRadius: '0.5rem',
                                background: 'var(--accent-coral)',
                                color: '#fff',
                                border: 'none',
                                cursor: 'pointer',
                            }}
                        >
                            홈으로 돌아가기
                        </button>
                    </div>
                ) : (
                    <>
                        <div className="loading-stage">
                            <span className="stage-icon"><CurrentIcon className="w-6 h-6" /></span>
                            <span className="stage-name">{STAGES[safeStage].name}</span>
                        </div>

                        <div className="loading-progress">
                            <div className="progress-bar-large">
                                <div
                                    className="progress-fill-large"
                                    style={{ width: `${Math.min(progress, 100)}%`, transition: 'width 0.5s ease' }}
                                ></div>
                            </div>
                            <span className="progress-text">{Math.min(progress, 100)}%</span>
                        </div>

                        <div className="loading-steps">
                            {STAGES.map((s, index) => (
                                <div
                                    key={index}
                                    className={`step ${index < safeStage ? 'done' : ''} ${index === safeStage ? 'active' : ''}`}
                                >
                                    <div className="step-dot"></div>
                                    <span>{s.name.replace('...', '').replace('!', '')}</span>
                                </div>
                            ))}
                        </div>

                        {done && (
                            <p style={{ marginTop: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                                분석 페이지로 이동합니다...
                            </p>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}

export default LoadingPage;
