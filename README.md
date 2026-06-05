# 01-cdp-dos
Ataque DoS mediante protocolo CDP


## Objetivo del Laboratorio
Demostrar cómo un atacante puede causar una denegación de servicio
en switches Cisco mediante la inundación del protocolo CDP con
entradas falsas, agotando la memoria del dispositivo.

---

## Objetivo del Script
Generar paquetes CDP maliciosos con Device-IDs aleatorios para
saturar la tabla de vecinos CDP del switch víctima.

### Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `-i` | Interfaz de red (ej: ens3) | Obligatorio |
| `-c` | Cantidad de paquetes (0=infinito) | 1000 |
| `-d` | Delay entre paquetes en segundos | 0.01 |
| `-v` | Modo verbose | False |

### Requisitos
- Sistema operativo: Kali Linux / Ubuntu
- Python 3.8+
- Scapy: `pip3 install scapy`
- Privilegios root

## Topologia de red
<img width="512" height="356" alt="image" src="https://github.com/user-attachments/assets/9526e1e3-e05f-445b-a487-f4b6c68c2e6b" />


| Dispositivo | Interfaz | IP |
|---|---|---|
| Ubuntu-Atacante | ens3 | 192.168.67.50/24 |
| SW-Core | e0/0 - e0/1 | — |
| Linux-Victima | ens3 | 192.168.67.60/24 |

---

## Funcionamiento del Script

1. Genera un Device-ID, Platform y Port-ID aleatorios
2. Construye el frame: `Ethernet → LLC → SNAP → CDP TLVs`
3. Envía al multicast `01:00:0c:cc:cc:cc` (dirección CDP)
4. Cada paquete usa una MAC de origen diferente
5. El switch agrega cada "vecino" a su tabla CDP hasta agotarla

---

## Uso

```bash
# Ataque básico
sudo python3 cdp_dos.py -i ens3

# Enviar 5000 paquetes con verbose
sudo python3 cdp_dos.py -i ens3 -c 5000 -v

# Ataque continuo sin límite
sudo python3 cdp_dos.py -i ens3 -c 0 -d 0.005
```


## Contramedidas

### En el switch Cisco
```cisco
! Deshabilitar CDP en puertos de usuarios
interface range FastEthernet0/1-24
 no cdp enable

! Mantener CDP solo en uplinks
interface GigabitEthernet0/1
 cdp enable
```

### Verificación de la contramedida
```cisco
show cdp neighbors
show cdp interface
```

## Video demostrativo 
https://youtu.be/T8mbxwYeMqI

