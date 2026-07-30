# Detecção de frameworks

**Público:** engenharia  
**Dono:** Engenharia ASEP | **Versão:** 1.0 | **Status:** vigente

Frameworks suportados inicialmente:

| Ecossistema | Frameworks |
|---|---|
| Python | FastAPI, Flask, Django, Streamlit |
| JavaScript | React, Next.js, Vue, Angular, Express |

As evidências são dependências declaradas, imports textuais e arquivos
convencionais (`manage.py`, `next.config.*`). Cada resultado registra suas
evidências. Não há execução do código analisado nem resolução de packages.

Uma detecção significa “há evidência compatível”, não certificação da
arquitetura ou de que o framework esteja ativo em produção.
