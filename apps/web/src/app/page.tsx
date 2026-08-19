"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  FieldError,
  Form,
  Input,
  Label,
  Modal,
  Spinner,
  TextArea,
  TextField,
} from "@heroui/react";

import { ApiError, createMeeting, listMeetings, type Meeting } from "@/lib/api";
import { clearSession, getSession, type Session } from "@/lib/auth";

const RECENT_MEETINGS_COUNT = 3;

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "medium",
  timeStyle: "short",
});

function toDatetimeLocalMin(): string {
  const now = new Date();
  now.setSeconds(0, 0);
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60_000).toISOString().slice(0, 16);
}

function MeetingList({
  meetings,
  error,
  isLoading,
  emptyMessage,
}: {
  meetings: Meeting[];
  error: string | null;
  isLoading: boolean;
  emptyMessage: string;
}) {
  if (error) {
    return (
      <Alert status="danger">
        <Alert.Indicator />
        <Alert.Content>
          <Alert.Description>{error}</Alert.Description>
        </Alert.Content>
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner aria-label="Загрузка встреч" size="lg" />
      </div>
    );
  }

  if (meetings.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted">{emptyMessage}</p>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {meetings.map((meeting) => (
        <li
          className="rounded-lg border border-border px-4 py-3"
          key={meeting.id}
        >
          <p className="font-medium">{meeting.title}</p>
          {meeting.description ? (
            <p className="mt-1 text-sm text-muted">{meeting.description}</p>
          ) : null}
          <p className="mt-2 text-xs text-muted">
            {dateFormatter.format(new Date(meeting.scheduled_at))}
          </p>
        </li>
      ))}
    </ul>
  );
}

export default function Home() {
  const router = useRouter();
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [meetings, setMeetings] = useState<Meeting[] | null>(null);
  const [meetingsError, setMeetingsError] = useState<string | null>(null);
  const [isLoadingMeetings, setIsLoadingMeetings] = useState(true);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    // localStorage only exists client-side, so the session can't be read
    // during the initial render (SSR/hydration) — it's read post-mount here.
    const current = getSession();
    if (!current) {
      router.replace("/login");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSession(current);
  }, [router]);

  useEffect(() => {
    if (!session) return;

    let cancelled = false;

    listMeetings(session.token)
      .then((data) => {
        if (!cancelled) setMeetings(data);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          router.replace("/login");
          return;
        }
        setMeetingsError(
          error instanceof ApiError
            ? error.message
            : "Не удалось подключиться к серверу. Проверьте соединение и попробуйте снова.",
        );
      })
      .finally(() => {
        if (!cancelled) setIsLoadingMeetings(false);
      });

    return () => {
      cancelled = true;
    };
  }, [session, router]);

  const handleLogout = () => {
    clearSession();
    router.push("/login");
  };

  const handleCreateMeeting = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!session) return;

    const formData = new FormData(e.currentTarget);
    const title = String(formData.get("title") ?? "").trim();
    const description = String(formData.get("description") ?? "").trim();
    const scheduledAt = String(formData.get("scheduled_at") ?? "");

    if (!title || !scheduledAt) return;

    setCreateError(null);
    setIsCreating(true);
    try {
      const meeting = await createMeeting(session.token, {
        title,
        description: description || null,
        scheduled_at: new Date(scheduledAt).toISOString(),
      });
      setMeetings((prev) => (prev ? [...prev, meeting] : [meeting]));
      setIsCreateOpen(false);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearSession();
        router.replace("/login");
        return;
      }
      setCreateError(
        error instanceof ApiError
          ? error.message
          : "Не удалось подключиться к серверу. Проверьте соединение и попробуйте снова.",
      );
    } finally {
      setIsCreating(false);
    }
  };

  if (!session) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <Spinner aria-label="Загрузка" size="lg" />
      </main>
    );
  }

  const allMeetings = meetings ?? [];
  const recentMeetings = [...allMeetings]
    .reverse()
    .slice(0, RECENT_MEETINGS_COUNT);

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <span className="font-semibold">Видеовстречи</span>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted">{session.email}</span>
          <Button onPress={handleLogout} size="sm" variant="secondary">
            Выйти
          </Button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-8">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">
            Здравствуйте, {session.email}!
          </h1>
          <p className="text-sm text-muted">
            Здесь собраны все ваши видеовстречи
          </p>
        </div>

        <Modal isOpen={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <Button className="self-start">Создать встречу</Button>
          <Modal.Backdrop>
            <Modal.Container>
              <Modal.Dialog className="sm:max-w-md">
                <Modal.CloseTrigger />
                <Modal.Header>
                  <Modal.Heading>Новая встреча</Modal.Heading>
                </Modal.Header>
                <Form className="contents" onSubmit={handleCreateMeeting}>
                  <Modal.Body>
                    <div className="flex flex-col gap-4">
                      {createError ? (
                        <Alert status="danger">
                          <Alert.Indicator />
                          <Alert.Content>
                            <Alert.Description>{createError}</Alert.Description>
                          </Alert.Content>
                        </Alert>
                      ) : null}

                      <TextField isRequired name="title" variant="secondary">
                        <Label>Название</Label>
                        <Input placeholder="Например, планёрка команды" />
                        <FieldError />
                      </TextField>

                      <TextField name="description" variant="secondary">
                        <Label>Описание</Label>
                        <TextArea placeholder="Необязательно" rows={3} />
                      </TextField>

                      <TextField
                        isRequired
                        name="scheduled_at"
                        type="datetime-local"
                        variant="secondary"
                      >
                        <Label>Дата и время</Label>
                        <Input min={toDatetimeLocalMin()} />
                        <FieldError />
                      </TextField>
                    </div>
                  </Modal.Body>
                  <Modal.Footer>
                    <Button
                      isDisabled={isCreating}
                      slot="close"
                      variant="secondary"
                    >
                      Отмена
                    </Button>
                    <Button isPending={isCreating} type="submit">
                      {isCreating ? "Создание..." : "Создать"}
                    </Button>
                  </Modal.Footer>
                </Form>
              </Modal.Dialog>
            </Modal.Container>
          </Modal.Backdrop>
        </Modal>

        <Card>
          <Card.Header>
            <Card.Title>Все встречи</Card.Title>
            <Card.Description>Полный список ваших встреч</Card.Description>
          </Card.Header>
          <Card.Content className="max-h-96 overflow-y-auto">
            <MeetingList
              emptyMessage="У вас пока нет встреч"
              error={meetingsError}
              isLoading={isLoadingMeetings}
              meetings={allMeetings}
            />
          </Card.Content>
        </Card>

        <Card>
          <Card.Header>
            <Card.Title>Последние встречи</Card.Title>
            <Card.Description>
              {RECENT_MEETINGS_COUNT} последние созданные встречи
            </Card.Description>
          </Card.Header>
          <Card.Content>
            <MeetingList
              emptyMessage="У вас пока нет встреч"
              error={meetingsError}
              isLoading={isLoadingMeetings}
              meetings={recentMeetings}
            />
          </Card.Content>
        </Card>
      </main>
    </div>
  );
}
