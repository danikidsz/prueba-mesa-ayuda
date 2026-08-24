// frontend/src/app/solicitudes.service.ts  (archivo NUEVO)
// Servicio que centraliza toda la comunicacion con la API propia.
// El componente nunca llama a HttpClient directo: mismo principio de
// desacoplamiento que el modulo IA del backend.
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Solicitud {
  id: string;
  asunto: string;
  descripcion: string;
  area: string;
  solicitante: string;
  estado: string;
  fecha_creacion: string;
}

export interface Clasificacion {
  categoria: string;
  prioridad: string;
  origen: string;
}

const API = 'http://localhost:8000';

@Injectable({ providedIn: 'root' })
export class SolicitudesService {
  private http = inject(HttpClient);

  listar(area?: string, estado?: string): Observable<Solicitud[]> {
    const params: Record<string, string> = {};
    if (area) params['area'] = area;
    if (estado) params['estado'] = estado;
    return this.http.get<Solicitud[]>(`${API}/solicitudes`, { params });
  }

  crear(datos: {
    asunto: string;
    descripcion: string;
    area: string;
    solicitante: string;
  }): Observable<Solicitud> {
    return this.http.post<Solicitud>(`${API}/solicitudes`, datos);
  }

  clasificar(texto: string): Observable<Clasificacion> {
    return this.http.post<Clasificacion>(`${API}/clasificar`, { texto });
  }
}