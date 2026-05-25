from pathlib import Path
import uuid
from fastapi import APIRouter, Request, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from database import engine
from m_transacciones import Transaccion
from m_usuarios import Usuario

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def panel_transacciones(
    request: Request,
    es_fraude: Optional[bool] = Query(None, description="Filtrar por fraude"),
    revisado: Optional[str] = Query(None, description="Filtrar por revisión"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    q: Optional[str] = Query(None, description="Búsqueda por ID de transacción o usuario"),
    offset: int = Query(0, ge=0),
):
    async with AsyncSession(engine) as session:
        base = select(Transaccion)
        count_base = select(func.count()).select_from(Transaccion)

        if es_fraude is not None:
            base = base.where(Transaccion.es_fraude == es_fraude)
            count_base = count_base.where(Transaccion.es_fraude == es_fraude)
        if revisado:
            base = base.where(Transaccion.revisado == revisado)
            count_base = count_base.where(Transaccion.revisado == revisado)
        if categoria:
            base = base.where(Transaccion.categoria == categoria)
            count_base = count_base.where(Transaccion.categoria == categoria)
        if q:
            try:
                uid = uuid.UUID(q)
                base = base.where(
                    (Transaccion.id_transaccion == uid) | (Transaccion.id_usuario == uid)
                )
                count_base = count_base.where(
                    (Transaccion.id_transaccion == uid) | (Transaccion.id_usuario == uid)
                )
            except ValueError:
                base = base.where(Transaccion.categoria.ilike(f"%{q}%"))
                count_base = count_base.where(Transaccion.categoria.ilike(f"%{q}%"))

        count_result = await session.execute(count_base)
        total = count_result.scalar() or 0

        base = base.order_by(Transaccion.fecha.desc()).offset(offset)
        resultado = await session.execute(base)
        transacciones = resultado.scalars().all()

        return templates.TemplateResponse(
            "transacciones.html",
            {
                "request": request,
                "transacciones": transacciones,
                "total": total,
                "es_fraude": es_fraude,
                "revisado": revisado,
                "categoria": categoria,
                "q": q,
                "offset": offset,
            },
        )


@router.get("/transaccion/{id_transaccion}", response_class=HTMLResponse)
async def detalle_transaccion(request: Request, id_transaccion: uuid.UUID):
    async with AsyncSession(engine) as session:
        stmt = select(Transaccion).where(Transaccion.id_transaccion == id_transaccion)
        resultado = await session.execute(stmt)
        transaccion = resultado.scalar_one_or_none()

        if not transaccion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transacción no encontrada",
            )

        return templates.TemplateResponse(
            "transaccion_detalle.html",
            {"request": request, "t": transaccion},
        )


@router.get("/cliente/{id_usuario}", response_class=HTMLResponse)
async def detalle_cliente(request: Request, id_usuario: uuid.UUID):
    async with AsyncSession(engine) as session:
        stmt_cliente = select(Usuario).where(Usuario.Clienteid == id_usuario)
        resultado_cliente = await session.exec(stmt_cliente)
        cliente = resultado_cliente.first()

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )

        stmt_trans = (
            select(Transaccion)
            .where(Transaccion.id_usuario == id_usuario)
            .order_by(Transaccion.fecha.desc())
        )
        resultado_trans = await session.execute(stmt_trans)
        transacciones = resultado_trans.scalars().all()

        fraud_count = sum(1 for t in transacciones if t.es_fraude)
        review_count = sum(1 for t in transacciones if t.revisar)

        return templates.TemplateResponse(
            "cliente_detalle.html",
            {
                "request": request,
                "cliente": cliente,
                "transacciones": transacciones,
                "fraud_count": fraud_count,
                "review_count": review_count,
            },
        )
