import type { PropsWithChildren, ReactNode } from "react";

type CardProps = PropsWithChildren<{
  title: string;
  eyebrow?: string;
  action?: ReactNode;
}>;

export function Card({ children, title, eyebrow, action }: CardProps) {
  return (
    <article className="card">
      <header className="card__header">
        <div>
          {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
          <h2>{title}</h2>
        </div>
        {action}
      </header>
      <div className="card__content">{children}</div>
    </article>
  );
}
