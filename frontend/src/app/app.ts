// frontend/src/app/app.ts  (REEMPLAZA el contenido actual)
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import {
  SolicitudesService,
  Solicitud,
  Clasificacion,
} from './solicitudes.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private servicio = inject(SolicitudesService);

  solicitudes = signal<Solicitud[]>([]);
  cargando = signal(false);
  error = signal('');

  filtroArea = '';
  filtroEstado = '';

  nueva = { asunto: '', descripcion: '', area: '', solicitante: '' };
  creando = signal(false);

  textoClasificar = '';
  clasificacion = signal<Clasificacion | null>(null);
  clasificando = signal(false);

  ngOnInit() {
    this.cargar();
  }

  cargar() {
    this.cargando.set(true);
    this.error.set('');
    this.servicio.listar(this.filtroArea, this.filtroEstado).subscribe({
      next: (datos) => {
        this.solicitudes.set(datos);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudo conectar con la API. ¿Está corriendo en el puerto 8000?');
        this.cargando.set(false);
      },
    });
  }

  limpiarFiltros() {
    this.filtroArea = '';
    this.filtroEstado = '';
    this.cargar();
  }

  crear() {
    this.creando.set(true);
    this.error.set('');
    this.servicio.crear(this.nueva).subscribe({
      next: () => {
        this.nueva = { asunto: '', descripcion: '', area: '', solicitante: '' };
        this.creando.set(false);
        this.cargar();
      },
      error: (e) => {
        this.error.set(
          e.status === 422
            ? 'Datos inválidos: revise que el asunto tenga al menos 5 caracteres y el solicitante 5.'
            : 'No se pudo crear la solicitud.'
        );
        this.creando.set(false);
      },
    });
  }

  clasificar() {
    this.clasificando.set(true);
    this.clasificacion.set(null);
    this.servicio.clasificar(this.textoClasificar).subscribe({
      next: (r) => {
        this.clasificacion.set(r);
        this.clasificando.set(false);
      },
      error: () => {
        this.error.set('No se pudo clasificar el texto.');
        this.clasificando.set(false);
      },
    });
  }
}