import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const MyApp());
}

/// URL del microservicio CBR
/* const String cbrEndpoint = "http://localhost:8000/cbr/recomendar"; */
const String cbrEndpoint = "http://10.227.246.94:8000/cbr/recomendar";

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CBR Café Cauca',
      theme: ThemeData(useMaterial3: true),
      home: const CbrFormPage(),
    );
  }
}

class CbrFormPage extends StatefulWidget {
  const CbrFormPage({super.key});

  @override
  State<CbrFormPage> createState() => _CbrFormPageState();
}

class _CbrFormPageState extends State<CbrFormPage> {
  final _formKey = GlobalKey<FormState>();

  // Controladores de texto
  final _ubicacionCtrl = TextEditingController(text: "Popayán");
  final _altitudCtrl = TextEditingController(text: "1678");
  final _sombraCtrl = TextEditingController(text: "25");
  final _tempMediaCtrl = TextEditingController(text: "17.6");
  final _humedadCtrl = TextEditingController(text: "97");
  final _precTotalCtrl = TextEditingController(text: "192.2");
  final _diasLluviaCtrl = TextEditingController(text: "18");
  final _brilloSolarCtrl = TextEditingController(text: "95");
  final _mdsCtrl = TextEditingController(text: "10"); // meses_despues_siembra
  final _edadViveroCtrl = TextEditingController(text: "3");

  // Selecciones
  String _tipo = "auto";
  String _mes = "noviembre";
  String? _luna = "creciente";
  String? _fase = "vivero_establecimiento";

  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _responseData;

  final List<String> _tipos = const [
    "auto",
    "almacigos",
    "fertilizacion_sin_analisis",
    "broca",
  ];

  final List<String> _meses = const [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
  ];

  final List<String> _fases = const [
    "vivero_establecimiento",
    "floracion_llenado",
    "cosecha_poscosecha",
  ];

  final List<String> _lunas = const [
    "nueva",
    "creciente",
    "llena",
    "menguante",
  ];

  @override
  void dispose() {
    _ubicacionCtrl.dispose();
    _altitudCtrl.dispose();
    _sombraCtrl.dispose();
    _tempMediaCtrl.dispose();
    _humedadCtrl.dispose();
    _precTotalCtrl.dispose();
    _diasLluviaCtrl.dispose();
    _brilloSolarCtrl.dispose();
    _mdsCtrl.dispose();
    _edadViveroCtrl.dispose();
    super.dispose();
  }

  Future<void> _consultarCbr() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _loading = true;
      _error = null;
      _responseData = null;
    });

    double parseDouble(String text) => double.parse(text.replaceAll(',', '.'));

    try {
      // Decidimos qué campo mandar según la fase
      double? mdsVal;
      double? edadViveroVal;

      if (_fase == "vivero_establecimiento") {
        // Solo usamos edad vivero
        edadViveroVal = _edadViveroCtrl.text.trim().isEmpty
            ? null
            : parseDouble(_edadViveroCtrl.text);
        mdsVal = null;
      } else {
        // En floración / cosecha usamos MDS
        mdsVal = _mdsCtrl.text.trim().isEmpty
            ? null
            : parseDouble(_mdsCtrl.text);
        edadViveroVal = null;
      }

      final body = <String, dynamic>{
        "data": ["CBR_Cafe_Cauca_A.yaml", "CBR_Cafe_Cauca_B_historicos.yaml"],
        "tipo": _tipo,
        "ubicacion": _ubicacionCtrl.text.trim().isEmpty
            ? null
            : _ubicacionCtrl.text.trim(),
        "altitud": parseDouble(_altitudCtrl.text),
        "mes": _mes,
        "variedad": null,
        "sombra": parseDouble(_sombraCtrl.text),
        "temp_media": parseDouble(_tempMediaCtrl.text),
        "humedad": parseDouble(_humedadCtrl.text),
        "prec_total_mm": parseDouble(_precTotalCtrl.text),
        "dias_lluvia": _diasLluviaCtrl.text.trim().isEmpty
            ? null
            : parseDouble(_diasLluviaCtrl.text),
        "brillo_solar": _brilloSolarCtrl.text.trim().isEmpty
            ? null
            : parseDouble(_brilloSolarCtrl.text),
        "meses_despues_siembra": mdsVal,
        "edad_vivero_meses": edadViveroVal,
        "luna": _luna,
        "fase": _fase,
        // Valores fijos que ya no se editan en la UI
        "k": 3,
        "kB": 3,
        "usar_extras_b": true,
        "save_case_to": "CBR_Cafe_Cauca_C.yaml",
      };

      final resp = await http.post(
        Uri.parse(cbrEndpoint),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(body),
      );

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        setState(() {
          _responseData = data;
        });
      } else {
        setState(() {
          _error = "Error ${resp.statusCode}: ${resp.body}";
        });
      }
    } catch (e) {
      setState(() {
        _error = "Error al llamar al CBR: $e";
      });
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  Widget _buildNumberField(
    TextEditingController controller,
    String label, {
    String? hint,
    bool required = true,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: const TextInputType.numberWithOptions(
        decimal: true,
        signed: false,
      ),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        border: const OutlineInputBorder(),
      ),
      validator: (value) {
        if (!required && (value == null || value.trim().isEmpty)) {
          return null;
        }
        if (value == null || value.trim().isEmpty) {
          return "Requerido";
        }
        final v = value.replaceAll(',', '.');
        if (double.tryParse(v) == null) {
          return "Debe ser numérico";
        }
        return null;
      },
    );
  }

  Widget _buildTextField(
    TextEditingController controller,
    String label, {
    bool required = true,
  }) {
    return TextFormField(
      controller: controller,
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
      ),
      validator: (value) {
        if (!required) return null;
        if (value == null || value.trim().isEmpty) {
          return "Requerido";
        }
        return null;
      },
    );
  }

  Widget _buildDropdown<T>({
    required String label,
    required T? value,
    required List<T> items,
    required void Function(T?) onChanged,
  }) {
    return InputDecorator(
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<T>(
          value: value,
          isExpanded: true,
          onChanged: onChanged,
          items: items
              .map(
                (e) => DropdownMenuItem<T>(value: e, child: Text(e.toString())),
              )
              .toList(),
        ),
      ),
    );
  }

  Widget _buildResultados() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Text(_error!, style: const TextStyle(color: Colors.red));
    }
    if (_responseData == null) {
      return const Text("Sin resultados aún. Llena el formulario y consulta.");
    }

    final resultadosA =
        _responseData!["resultados_A"] as Map<String, dynamic>? ?? {};

    final extrasAgrupados =
        _responseData!["extras_B_agrupados"] as Map<String, dynamic>? ?? {};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          "Resultados CBR",
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const Text(
          "Recomendaciones específicas:",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        ...["almacigos", "fertilizacion_sin_analisis", "broca"].map((dom) {
          final domData = resultadosA[dom] as Map<String, dynamic>? ?? {};
          final aplic = domData["aplicabilidad"] as Map<String, dynamic>? ?? {};
          final aplica = aplic["aplica"] ?? true;
          final razonNo = aplic["razon_no_aplica"];

          final hits = (domData["hits"] as List<dynamic>? ?? [])
              .cast<dynamic>();
          final recs =
              domData["recomendaciones"] as Map<String, dynamic>? ?? {};
          final tecnicas = (recs["tecnicas"] as List<dynamic>? ?? [])
              .cast<dynamic>();
          final trads = (recs["tradicionales"] as List<dynamic>? ?? [])
              .cast<dynamic>();

          return Card(
            margin: const EdgeInsets.symmetric(vertical: 6),
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    dom.toUpperCase(),
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (!aplica) ...[
                    const SizedBox(height: 4),
                    Text(
                      "No aplicable: $razonNo",
                      style: const TextStyle(color: Colors.orange),
                    ),
                  ] else ...[
                    const SizedBox(height: 6),
                    const Text(
                      "Casos similares:",
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    if (hits.isEmpty)
                      const Text("No se encontraron casos similares"),
                    ...hits.map((h) {
                      final id = h["id"] ?? "?";
                      final ubi = h["ubicacion"] ?? "N/D";
                      final sim = h["similitud"] ?? 0.0;
                      return Text("• $id ($ubi)  → similitud: $sim");
                    }),
                    if (tecnicas.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      const Text(
                        "Recomendaciones técnicas:",
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      ...tecnicas.map((t) => Text("- $t")),
                    ],
                    if (trads.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      const Text(
                        "Recomendaciones tradicionales:",
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      ...trads.map((t) => Text("- $t")),
                    ],
                  ],
                ],
              ),
            ),
          );
        }),
        if (extrasAgrupados.isNotEmpty) ...[
          const SizedBox(height: 8),
          const Text(
            "Recomendaciones generales:",
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          ...extrasAgrupados.entries.map((e) {
            final cat = e.key;
            final lista = (e.value as List<dynamic>? ?? [])
                .cast<dynamic>()
                .toList();
            return Card(
              margin: const EdgeInsets.symmetric(vertical: 4),
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "Categoría: $cat",
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    ...lista.map((txt) => Text("- $txt")),
                  ],
                ),
              ),
            );
          }),
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final padding = MediaQuery.of(context).size.width > 600 ? 24.0 : 12.0;

    return Scaffold(
      appBar: AppBar(title: const Text("CBR Café – Cauca")),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(padding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Form(
              key: _formKey,
              child: Column(
                children: [
                  _buildTextField(_ubicacionCtrl, "Ubicación"),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _buildNumberField(
                          _altitudCtrl,
                          "Altitud (msnm)",
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: _buildNumberField(_sombraCtrl, "Sombra (%)"),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _buildDropdown<String>(
                          label: "Mes",
                          value: _mes,
                          items: _meses,
                          onChanged: (v) => setState(() => _mes = v ?? _mes),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: _buildDropdown<String>(
                          label: "Tipo",
                          value: _tipo,
                          items: _tipos,
                          onChanged: (v) => setState(() => _tipo = v ?? _tipo),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _buildDropdown<String?>(
                          label: "Fase fenológica",
                          value: _fase,
                          items: _fases,
                          onChanged: (v) => setState(() => _fase = v),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: _buildDropdown<String?>(
                          label: "Fase lunar",
                          value: _luna,
                          items: _lunas,
                          onChanged: (v) => setState(() => _luna = v),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _buildNumberField(
                          _tempMediaCtrl,
                          "Temp. media (°C)",
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: _buildNumberField(_humedadCtrl, "Humedad (%)"),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _buildNumberField(
                          _precTotalCtrl,
                          "Precipitación (mm)",
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: _buildNumberField(
                          _diasLluviaCtrl,
                          "Días de lluvia",
                          required: false,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  _buildNumberField(
                    _brilloSolarCtrl,
                    "Brillo solar",
                    required: false,
                  ),
                  const SizedBox(height: 8),

                  // Campo dinámico según fase
                  if (_fase == "vivero_establecimiento") ...[
                    _buildNumberField(
                      _edadViveroCtrl,
                      "Edad vivero (meses)",
                      required: false,
                    ),
                  ] else ...[
                    _buildNumberField(
                      _mdsCtrl,
                      "Meses después de siembra (MDS)",
                      required: false,
                    ),
                  ],

                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _loading ? null : _consultarCbr,
                      icon: const Icon(Icons.search),
                      label: const Text("Consultar"),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _buildResultados(),
          ],
        ),
      ),
    );
  }
}
