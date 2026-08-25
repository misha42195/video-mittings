"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Alert, Button, Card, Spinner } from "@heroui/react";

import {
  ApiError,
  getMeeting,
  listMeetingFiles,
  uploadMeetingFile,
  type Meeting,
  type MeetingFile,
} from "@/lib/api";
import { clearSession, getSession, type Session } from "@/lib/auth";

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

function fileTypeIcon(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (["mp4", "mov"].includes(ext)) return "🎬";
  if (["wav", "mp3"].includes(ext)) return "🎵";
  if (ext === "pdf") return "📄";
  if (ext === "docx") return "📝";
  return "📎";
}

const ALLOWED_EXTS = new Set([".mp4", ".mov", ".wav", ".mp3", ".pdf", ".docx"]);
const MAX_SIZE = 100 * 1024 * 1024;

export default function MeetingPage() {
  const params = useParams<{ id: string | string[] }>();
  const router = useRouter();
  const rawId = Array.isArray(params.id) ? params.id[0] : params.id;
  const meetingId = Number(rawId);

  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [meetingError, setMeetingError] = useState<string | null>(null);
  const [isLoadingMeeting, setIsLoadingMeeting] = useState(true);

  const [files, setFiles] = useState<MeetingFile[] | null>(null);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);

  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const current = getSession();
    if (!current) {
      router.replace("/login");
      return;
    }
    setSession(current);
  }, [router]);

  useEffect(() => {
    if (!session) return;

    if (!Number.isFinite(meetingId)) {
      setMeetingError("Встреча не найдена");
      setFilesError("Встреча не найдена");
      setIsLoadingMeeting(false);
      setIsLoadingFiles(false);
      return;
    }

    let cancelled = false;

    getMeeting(session.token, meetingId)
      .then((data) => {
        if (!cancelled) setMeeting(data);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          router.replace("/login");
          setIsLoadingMeeting(false);
          setIsLoadingFiles(false);
          return;
        }
        if (error instanceof ApiError && error.status === 404) {
          setMeetingError("Встреча не найдена");
          return;
        }
        setMeetingError(
          error instanceof ApiError
            ? error.message
            : "Не удалось загрузить встречу",
        );
      })
      .finally(() => {
        if (!cancelled) setIsLoadingMeeting(false);
      });

    listMeetingFiles(session.token, meetingId)
      .then((data) => {
        if (!cancelled) setFiles(data);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          router.replace("/login");
          setIsLoadingMeeting(false);
          setIsLoadingFiles(false);
          return;
        }
        if (error instanceof ApiError && error.status === 404) {
          setFilesError("Встреча не найдена");
          return;
        }
        setFilesError(
          error instanceof ApiError
            ? error.message
            : "Не удалось загрузить файлы",
        );
      })
      .finally(() => {
        if (!cancelled) setIsLoadingFiles(false);
      });

    return () => {
      cancelled = true;
    };
  }, [session, meetingId, router]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !session) return;

    // reset input to allow re-selecting same file
    e.target.value = "";
    setUploadError(null);

    // client-side validation
    const ext = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (!ALLOWED_EXTS.has(ext)) {
      setUploadError(
        "Недопустимый тип файла. Разрешены: docx, mov, mp3, mp4, pdf, wav",
      );
      return;
    }
    if (file.size > MAX_SIZE) {
      setUploadError("Файл слишком большой. Максимум 100 МБ");
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const uploaded = await uploadMeetingFile(
        session.token,
        meetingId,
        file,
        (pct) => {
          setUploadProgress(pct);
        },
      );
      setFiles((prev) => (prev ? [...prev, uploaded] : [uploaded]));
      setUploadProgress(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearSession();
        router.replace("/login");
        return;
      }
      setUploadError(
        error instanceof ApiError ? error.message : "Не удалось загрузить файл",
      );
      setUploadProgress(null);
    } finally {
      setIsUploading(false);
    }
  };

  if (!session) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <Spinner aria-label="Загрузка" size="lg" />
      </main>
    );
  }

  if (isLoadingMeeting) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <Spinner aria-label="Загрузка встречи" size="lg" />
      </main>
    );
  }

  if (meetingError) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-8">
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{meetingError}</Alert.Description>
          </Alert.Content>
        </Alert>
      </main>
    );
  }

  if (!meeting) return null;

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <button
          className="text-sm text-muted hover:text-foreground"
          onClick={() => router.push("/")}
          type="button"
        >
          ← На главную
        </button>
        <span className="text-sm text-muted">{session.email}</span>
      </header>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-8">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">{meeting.title}</h1>
          {meeting.description ? (
            <p className="text-sm text-muted">{meeting.description}</p>
          ) : null}
          <p className="text-xs text-muted">
            {dateFormatter.format(new Date(meeting.scheduled_at))}
          </p>
        </div>

        <Card>
          <Card.Header>
            <Card.Title>Файлы</Card.Title>
            <Card.Description>
              Записи, документы и презентации встречи
            </Card.Description>
          </Card.Header>
          <Card.Content className="flex flex-col gap-4">
            {/* hidden file input */}
            <input
              ref={fileInputRef}
              data-testid="file-input"
              type="file"
              accept=".mp4,.mov,.wav,.mp3,.pdf,.docx"
              className="hidden"
              onChange={handleFileChange}
              disabled={isUploading}
            />

            <div className="flex items-center gap-3">
              <Button
                isDisabled={isUploading}
                onPress={() => fileInputRef.current?.click()}
                variant="secondary"
              >
                Выбрать файл
              </Button>
              {isUploading ? (
                <Spinner size="sm" aria-label="Загрузка файла" />
              ) : null}
            </div>

            {uploadProgress !== null ? (
              <div
                data-testid="upload-progress"
                role="progressbar"
                aria-valuenow={uploadProgress}
                aria-valuemin={0}
                aria-valuemax={100}
                className="flex flex-col gap-1"
              >
                <div className="h-2 w-full overflow-hidden rounded bg-neutral-200">
                  <div
                    className="h-full bg-accent transition-all"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <span className="text-xs text-muted">{uploadProgress}%</span>
              </div>
            ) : null}

            {uploadError ? (
              <Alert status="danger" data-testid="upload-error">
                <Alert.Indicator />
                <Alert.Content>
                  <Alert.Description>{uploadError}</Alert.Description>
                </Alert.Content>
              </Alert>
            ) : null}

            {isLoadingFiles ? (
              <div className="flex justify-center py-4">
                <Spinner aria-label="Загрузка файлов" size="sm" />
              </div>
            ) : filesError ? (
              <Alert status="danger">
                <Alert.Indicator />
                <Alert.Content>
                  <Alert.Description>{filesError}</Alert.Description>
                </Alert.Content>
              </Alert>
            ) : files && files.length === 0 ? (
              <p
                data-testid="files-empty"
                className="py-4 text-center text-sm text-muted"
              >
                Файлов пока нет
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {files?.map((f) => (
                  <li
                    key={f.id}
                    data-testid="file-item"
                    className="flex items-center justify-between rounded-lg border border-border px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <span aria-hidden>
                        {fileTypeIcon(f.original_filename)}
                      </span>
                      <span className="text-sm font-medium">
                        {f.original_filename}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted">
                      <span>{formatSize(f.size)}</span>
                      <span>
                        {dateFormatter.format(new Date(f.created_at))}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card.Content>
        </Card>
      </main>
    </div>
  );
}
