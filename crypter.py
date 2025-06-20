import base64
import json
import uuid
import psutil


def _get_stable_mac_address():
    """
    Get a stable MAC address using psutil, falling back to uuid.
    """
    try:
        iface_addrs = psutil.net_if_addrs()
        sorted_ifaces = sorted(iface_addrs.keys())
        for interface in sorted_ifaces:
            snics = iface_addrs[interface]
            for snic in snics:
                is_valid_mac = (
                    snic.family == psutil.AF_LINK and
                    snic.address and
                    snic.address != "00:00:00:00:00:00"
                )
                if is_valid_mac:
                    return snic.address.upper()
    except Exception:
        pass
    mac = uuid.getnode()
    return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))


def _get_machine_key():
    """
    根据机器的MAC地址生成一个一致的、基本的加密密钥。
    这只用于基础的混淆，而非高强度安全加密。
    """
    # 获取MAC地址作为硬件ID
    mac_str = _get_stable_mac_address()
    # 将MAC地址转换为字符串并重复多次，以确保密钥足够长
    return mac_str.encode('utf-8') * 4


def _xor_cipher(data, key):
    """
    简单的异或加密/解密函数。
    """
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])


def encrypt(config_data):
    """
    加密配置字典。
    """
    key = _get_machine_key()
    json_data = json.dumps(config_data).encode('utf-8')
    encrypted_data = _xor_cipher(json_data, key)
    # 使用Base64编码，使其可以作为文本存储
    return base64.b64encode(encrypted_data).decode('utf-8')


def decrypt(encrypted_b64_data):
    """
    解密配置数据。
    """
    key = _get_machine_key()
    encrypted_data = base64.b64decode(encrypted_b64_data.encode('utf-8'))
    decrypted_data = _xor_cipher(encrypted_data, key)
    return json.loads(decrypted_data.decode('utf-8')) 