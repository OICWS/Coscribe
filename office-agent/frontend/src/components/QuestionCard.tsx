import { useState } from "react";
import type { CardAnswers, CardState } from "../lib/questionCards";
import type { QuestionSpec } from "../types/wire";
import { CheckIcon, ChevronRightIcon, PencilIcon } from "./icons";

/** A question card in the conversation (decision 0060). It never covers the conversation and
 * never holds the turn: the person answers by a click whenever they like, or in the message box
 * ("Or just reply in chat"), or not at all. One question answers on the click; several page
 * through, each with a line for an answer of the person's own, and go back together on Submit,
 * which shows once every question has an answer.
 * Answered, the card folds to the answer with a check. */
export function QuestionCardView({
  questions,
  state,
  onAnswer,
}: {
  questions: QuestionSpec[];
  state: CardState;
  onAnswer: (answers: CardAnswers) => void;
}) {
  if (questions.length === 0) return null;
  if (state.status === "answered") return <AnsweredCard questions={questions} answers={state.answers} inChat={state.inChat} />;
  if (state.status === "replaced") return <ReplacedCard questions={questions} />;
  return questions.length === 1 && !questions[0].multi_select ? (
    <SingleQuestion question={questions[0]} onAnswer={onAnswer} />
  ) : (
    <PagedQuestions questions={questions} onAnswer={onAnswer} />
  );
}

const CARD = "w-full rounded-[20px] border border-[var(--border)] bg-[var(--bg)] px-4 pb-3 pt-4";
const ROW = "flex w-full items-start gap-3.5 rounded-xl px-2.5 py-2.5 text-left";
const ROW_WRAP = "border-b border-[var(--border)] last:border-b-0 hover:border-transparent has-[:hover]:border-transparent";

const letter = (i: number) => String.fromCharCode(65 + i);

function focusComposer() {
  document.querySelector<HTMLTextAreaElement>('[data-testid="composer"] textarea')?.focus();
}

function ReplyInChat() {
  return (
    <div className="px-2.5 pt-2 text-[13px] text-[var(--muted)]">
      Or just{" "}
      <button type="button" className="text-[var(--fg)] underline underline-offset-2 hover:text-[var(--accent)]" onClick={focusComposer}>
        reply in chat
      </button>
      .
    </div>
  );
}

function Badge({ mark, active = false }: { mark: React.ReactNode; active?: boolean }) {
  return (
    <span
      className={`flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-lg text-[14px] ${
        active ? "bg-[var(--border)] text-[var(--fg)]" : "bg-[var(--card-bg)] text-[var(--muted)] group-hover:bg-[var(--border)] group-hover:text-[var(--fg)]"
      }`}
    >
      {mark}
    </span>
  );
}

/** `note` replaces the description on an answered card, which shows no Recommended badge. */
function OptionText({ option, answered = false, note }: { option: QuestionSpec["options"][number]; answered?: boolean; note?: string }) {
  return (
    <span className="min-w-0 pt-[3px]">
      <span className="block text-[15px] leading-snug">
        {option.label}
        {option.recommended && !answered && (
          <span className="ml-2 whitespace-nowrap rounded-full bg-[var(--accent-soft)] px-2 py-px align-[1px] text-[12px] text-[var(--accent)]">
            Recommended
          </span>
        )}
      </span>
      {(note ?? option.description) && <span className="mt-0.5 block text-[13px] text-[var(--muted)]">{note ?? option.description}</span>}
    </span>
  );
}

function OptionRows({
  question,
  picked,
  onPick,
}: {
  question: QuestionSpec;
  picked: ReadonlySet<string>;
  onPick: (label: string) => void;
}) {
  return (
    <>
      {question.options.map((option, i) => {
        const chosen = picked.has(option.label);
        return (
          <div key={option.label} className={ROW_WRAP}>
            <button
              type="button"
              aria-pressed={question.multi_select ? chosen : undefined}
              className={`${ROW} group hover:bg-[var(--card-bg)] ${chosen ? "bg-[var(--card-bg)]" : ""}`}
              onClick={() => onPick(option.label)}
            >
              <Badge mark={question.multi_select && chosen ? <CheckIcon className="h-3.5 w-3.5" /> : letter(i)} active={chosen} />
              <OptionText option={option} />
            </button>
          </div>
        );
      })}
    </>
  );
}

function SingleQuestion({ question, onAnswer }: { question: QuestionSpec; onAnswer: (answers: CardAnswers) => void }) {
  return (
    <div className={CARD}>
      <div className="px-1 pb-2 text-[15.5px]">{question.question}</div>
      <OptionRows question={question} picked={new Set()} onPick={(label) => onAnswer([label])} />
      <ReplyInChat />
    </div>
  );
}

/** One page per question; a single question that takes several choices pages too, since its
 * ticks need a Submit. */
function PagedQuestions({ questions, onAnswer }: { questions: QuestionSpec[]; onAnswer: (answers: CardAnswers) => void }) {
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState<Set<string>[]>(() => questions.map(() => new Set()));
  const [own, setOwn] = useState<string[]>(() => questions.map(() => ""));
  const answerOf = (i: number): string | null => {
    const labels = questions[i].options.map((o) => o.label).filter((l) => picked[i].has(l));
    const typed = own[i].trim();
    if (!questions[i].multi_select) return typed || labels[0] || null;
    const all = typed ? [...labels, typed] : labels;
    return all.length > 0 ? all.join(", ") : null;
  };
  const answers = questions.map((_, i) => answerOf(i));
  const question = questions[index];
  const paged = questions.length > 1;

  const pick = (label: string) => {
    const next = picked.map((set, i) => {
      if (i !== index) return set;
      if (!question.multi_select) return new Set([label]);
      const toggled = new Set(set);
      if (toggled.has(label)) toggled.delete(label);
      else toggled.add(label);
      return toggled;
    });
    setPicked(next);
    if (!question.multi_select) {
      setOwn(own.map((t, i) => (i === index ? "" : t)));
      const after = [...questions.keys()].slice(index + 1).find((i) => answerOf(i) === null);
      if (after !== undefined) setIndex(after);
    }
  };
  const type = (value: string) => {
    setOwn(own.map((t, i) => (i === index ? value : t)));
    if (!question.multi_select && value.trim()) setPicked(picked.map((set, i) => (i === index ? new Set() : set)));
  };

  return (
    <div className={CARD}>
      <div className="flex items-start justify-between gap-3 px-1 pb-2">
        <div className="min-w-0 text-[15.5px]">{question.question}</div>
        {paged && <Pager index={index} total={questions.length} onGo={setIndex} />}
      </div>
      <OptionRows key={index} question={question} picked={picked[index]} onPick={pick} />
      <div className="flex items-center gap-3.5 px-2.5 pt-2.5">
        <Badge mark={<PencilIcon className="h-3.5 w-3.5" />} active={own[index].trim() !== ""} />
        <input
          key={index}
          aria-label="Your own answer"
          className="min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-transparent px-2.5 py-1.5 text-sm outline-none placeholder:text-[var(--muted)] focus:border-[var(--border-hover)]"
          placeholder="Other: type your own answer"
          value={own[index]}
          onChange={(e) => type(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== "Enter" || e.nativeEvent.isComposing || !own[index].trim()) return;
            const after = [...questions.keys()].find((i) => i !== index && answers[i] === null);
            if (after !== undefined) setIndex(after);
          }}
        />
      </div>
      <Progress answers={answers} paged={paged} selected={picked[0].size + (own[0].trim() ? 1 : 0)} onSubmit={() => onAnswer(answers)} />
      <ReplyInChat />
    </div>
  );
}

function Pager({ index, total, onGo }: { index: number; total: number; onGo: (index: number) => void }) {
  const arrow = "rounded-md p-1 hover:bg-[var(--card-bg)] hover:text-[var(--fg)] disabled:opacity-40 disabled:hover:bg-transparent";
  return (
    <div className="flex shrink-0 items-center gap-1 text-[13px] tabular-nums text-[var(--muted)]">
      <button type="button" aria-label="Previous question" className={arrow} disabled={index === 0} onClick={() => onGo(index - 1)}>
        <ChevronRightIcon className="h-4 w-4 rotate-180" />
      </button>
      {index + 1} / {total}
      <button type="button" aria-label="Next question" className={arrow} disabled={index === total - 1} onClick={() => onGo(index + 1)}>
        <ChevronRightIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

/** How far the answers have got, and Submit once every question has one. */
function Progress({ answers, paged, selected, onSubmit }: { answers: CardAnswers; paged: boolean; selected: number; onSubmit: () => void }) {
  const count = answers.filter((a) => a !== null).length;
  return (
    <div className="mt-3 flex min-h-[44px] items-center justify-between gap-3 border-t border-[var(--border)] px-2.5 pt-3">
      <span className="flex items-center gap-2 text-[13px] text-[var(--muted)]">
        {paged && (
          <span className="flex gap-1.5" aria-hidden>
            {answers.map((a, i) => (
              <span key={i} className={`h-[7px] w-[7px] rounded-full ${a !== null ? "bg-[var(--accent)]" : "bg-[var(--border)]"}`} />
            ))}
          </span>
        )}
        {paged ? `${count} of ${answers.length} answered` : `${selected} selected`}
      </span>
      {count === answers.length && (
        <button
          type="button"
          className="rounded-lg bg-[var(--accent)] px-4 py-1.5 text-sm text-[var(--accent-fg)] hover:bg-[var(--accent-hover)]"
          onClick={onSubmit}
        >
          Submit
        </button>
      )}
    </div>
  );
}

function AnsweredCard({ questions, answers, inChat }: { questions: QuestionSpec[]; answers: CardAnswers; inChat: boolean }) {
  if (questions.length === 1) {
    const question = questions[0];
    const answer = answers[0] ?? null;
    const parts = answer === null ? [] : question.multi_select ? answer.split(", ") : [answer];
    const note = inChat ? "Answered in chat" : undefined;
    return (
      <div className="w-full rounded-[20px] bg-[var(--card-bg)] px-4 pb-4 pt-4">
        <div className="px-1 pb-2 text-[15.5px]">{question.question}</div>
        {answer === null ? (
          <div className="px-1 text-sm text-[var(--muted)]">Not answered</div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {parts.map((part) => {
              const i = question.options.findIndex((o) => o.label === part);
              return (
                <div key={part} className="flex items-center gap-3.5 rounded-xl bg-[color-mix(in_srgb,var(--fg)_5%,transparent)] px-2.5 py-2.5">
                  <Badge mark={i >= 0 ? letter(i) : <PencilIcon className="h-3.5 w-3.5" />} />
                  <OptionText option={i >= 0 ? question.options[i] : { label: part, description: "", recommended: false }} answered note={note} />
                  <CheckIcon className="ml-auto h-4 w-4 shrink-0 text-[var(--muted)]" aria-label="Answered" />
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="flex w-full flex-col gap-2.5 rounded-[20px] bg-[var(--card-bg)] px-5 py-4">
      {questions.map((q, i) => (
        <div key={i}>
          <div className="text-[13.5px] text-[var(--muted)]">{q.question}</div>
          {answers[i] ? (
            <div className="flex items-start gap-2 text-[15px]">
              <CheckIcon className="mt-[5px] h-3.5 w-3.5 shrink-0 text-[var(--muted)]" />
              <span className="min-w-0">{answers[i]}</span>
            </div>
          ) : (
            <div className="text-[15px] text-[var(--muted)]">Skipped</div>
          )}
        </div>
      ))}
      {inChat && <div className="text-[12.5px] text-[var(--muted)]">Answered in chat</div>}
    </div>
  );
}

function ReplacedCard({ questions }: { questions: QuestionSpec[] }) {
  return (
    <div className="w-full rounded-[20px] border border-dashed border-[var(--border)] px-5 py-3 text-[var(--muted)]">
      {questions.map((q, i) => (
        <div key={i} className="text-[14px]">
          {q.question}
        </div>
      ))}
      <div className="mt-1 text-[12.5px]">No longer needed: a newer question replaced it</div>
    </div>
  );
}
