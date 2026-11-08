// Desenha os gráficos da aba Gráficos. Todos os números já vêm calculados
// por logica.estatisticas() (Python); aqui só se trata a apresentação.
// O interface.py chama window.desenharGraficos(json) depois de montar a aba.
window.desenharGraficos = function (json) {
  var dados = JSON.parse(json);
  (window.__graficos || []).forEach(function (g) { g.destroy(); });
  window.__graficos = [];
  function novo(canvas, config) {
    var g = new Chart(canvas, config);
    window.__graficos.push(g);
    return g;
  }

  var COR_TIPO = {
    cliente: '#3d3c9b', prestador: '#2a9d8f', envelope: '#e9a23b',
    entrega: '#c8553d', outro: '#8a8fa8'
  };
  var ANIL = '#3d3c9b';

  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.font.size = 13;
  Chart.defaults.color = '#4a5170';
  Chart.defaults.borderColor = '#d5dbe8';
  Chart.defaults.maintainAspectRatio = false;

  function curto(texto) {
    return texto.length > 24 ? texto.slice(0, 23) + '…' : texto;
  }

  function semDados(idCanvas) {
    var area = document.getElementById(idCanvas).parentNode;
    area.textContent = '';
    var aviso = document.createElement('p');
    aviso.className = 'vazio';
    aviso.textContent = 'Sem dados neste período.';
    area.appendChild(aviso);
  }

  function ranking(idCanvas, lista, valor, rotuloEixo, detalhe) {
    if (!lista.length) { semDados(idCanvas); return; }
    novo(document.getElementById(idCanvas), {
      type: 'bar',
      data: {
        labels: lista.map(function (i) { return i.nome; }),
        datasets: [{ data: lista.map(valor), backgroundColor: ANIL, borderRadius: 3, maxBarThickness: 26 }]
      },
      options: {
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: {
            label: function (c) { return c.parsed.x + ' ' + rotuloEixo; },
            afterLabel: function (c) { return detalhe ? detalhe(lista[c.dataIndex]) : ''; }
          } }
        },
        scales: {
          x: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: rotuloEixo } },
          y: { grid: { display: false }, ticks: { callback: function (v) { return curto(this.getLabelForValue(v)); } } }
        }
      }
    });
  }

  // Registros por dia (ou semana), empilhados por tipo
  novo(document.getElementById('grafico-dia'), {
    type: 'bar',
    data: {
      labels: dados.por_dia.rotulos,
      datasets: dados.por_dia.series.map(function (s) {
        return { label: s.rotulo, data: s.valores, backgroundColor: COR_TIPO[s.tipo], maxBarThickness: 28 };
      })
    },
    options: {
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, boxHeight: 12 } } },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { maxRotation: 60, autoSkip: true } },
        y: { stacked: true, beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: 'Registros' } }
      }
    }
  });

  ranking('grafico-frequentes', dados.mais_frequentes,
          function (i) { return i.visitas; }, 'visitas');

  ranking('grafico-tempo', dados.maior_tempo,
          function (i) { return i.minutos; }, 'min no escritório',
          function (i) { return i.visitas + (i.visitas === 1 ? ' visita' : ' visitas') + ' com saída, média de ' + i.media + ' min'; });

  ranking('grafico-atendem', dados.mais_atenderam,
          function (i) { return i.visitas; }, 'registros');

  // Horários de maior movimento
  novo(document.getElementById('grafico-horas'), {
    type: 'bar',
    data: {
      labels: dados.horarios.rotulos,
      datasets: [{ data: dados.horarios.valores, backgroundColor: ANIL, borderRadius: 3, maxBarThickness: 32 }]
    },
    options: {
      plugins: { legend: { display: false },
                 tooltip: { callbacks: { label: function (c) { return c.parsed.y + ' registros'; } } } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: 'Registros' } }
      }
    }
  });

  // Situação das saídas
  var s = dados.saidas;
  var total = s.registrada + s.sem_registro + s.no_escritorio;
  if (!total) {
    semDados('grafico-saidas');
  } else {
    novo(document.getElementById('grafico-saidas'), {
      type: 'doughnut',
      data: {
        labels: ['Saída registrada', 'Sem saída registrada', 'Ainda no escritório'],
        datasets: [{ data: [s.registrada, s.sem_registro, s.no_escritorio],
                     backgroundColor: ['#1e7b5a', '#e9a23b', '#9aa3bf'], borderWidth: 2, borderColor: '#fbfcfe' }]
      },
      options: {
        cutout: '58%',
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 12, boxHeight: 12 } },
          tooltip: { callbacks: { label: function (c) {
            return c.label + ': ' + c.parsed + ' (' + Math.round(100 * c.parsed / total) + '%)';
          } } }
        }
      }
    });
  }
};
