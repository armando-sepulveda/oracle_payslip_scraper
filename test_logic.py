#!/usr/bin/env python3
"""
Script de prueba para verificar la lógica de continuación
"""

def simulate_download_logic():
    """Simula la lógica de descarga para verificar que funciona correctamente"""
    
    print("=== Simulación de lógica de continuación ===\n")
    
    # Simular escenarios
    scenarios = [
        {"name": "Inicio desde 0", "idx": 0, "total_files": 200},
        {"name": "Continuación desde 39", "idx": 39, "total_files": 200},
        {"name": "Continuación desde 95", "idx": 95, "total_files": 200},
        {"name": "Continuación desde 150", "idx": 150, "total_files": 200},
    ]
    
    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ---")
        idx = scenario['idx']
        total_files = scenario['total_files']
        
        # Simular carga de elementos (10 por clic)
        # Inicialmente hay 10 elementos visibles
        visible_elements = 10
        
        # Calcular cuántos clics necesitamos para tener visible el elemento idx
        clicks_needed = idx // 10
        
        print(f"Índice actual: {idx}")
        print(f"Elementos visibles inicialmente: {visible_elements}")
        print(f"Clics necesarios: {clicks_needed}")
        
        # Simular clics en "Cargar Más"
        for click in range(clicks_needed):
            visible_elements += 10
            print(f"  Clic {click + 1}: ahora hay {visible_elements} elementos visibles")
        
        # Verificar si podemos acceder al elemento
        if idx < visible_elements:
            print(f"✅ Puede acceder al elemento {idx} (visible en posición {idx})")
        else:
            print(f"❌ NO puede acceder al elemento {idx} (solo hay {visible_elements} visibles)")
        
        # Simular proceso del siguiente elemento
        next_idx = idx + 1
        next_clicks_needed = next_idx // 10
        
        print(f"\nDespués de procesar, para el siguiente elemento ({next_idx}):")
        print(f"  Clics necesarios: {next_clicks_needed}")
        
        # Calcular elementos visibles después de recargar
        visible_after_reload = 10 + (next_clicks_needed * 10)
        print(f"  Elementos visibles después de recargar: {visible_after_reload}")
        
        if next_idx < visible_after_reload:
            print(f"✅ Siguiente elemento {next_idx} será accesible")
        else:
            print(f"❌ Siguiente elemento {next_idx} NO será accesible")


if __name__ == "__main__":
    simulate_download_logic()
