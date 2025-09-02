import asyncio
import aioping
from log import logger
from typing import List, Tuple, Dict, Optional

async def ping_server(host: str, timeout: float = 2, retries: int = 3) -> Optional[float]:
    """
    异步 ping 单个服务器并返回延迟
    
    参数:
        host: 服务器地址
        timeout: 每次尝试的超时时间(秒)
        retries: 最大重试次数
        
    返回:
        平均延迟(毫秒) 或 None(如果服务器不可达)
    """
    total_latency = 0.0
    successful_pings = 0
    
    for attempt in range(retries):
        try:
            # 发送异步 ping 请求
            delay = await aioping.ping(host, timeout=timeout) * 1000  # 转换为毫秒
            total_latency += delay
            successful_pings += 1
        except (TimeoutError, OSError):
            # 超时或网络错误，继续尝试
            continue
        except Exception as e:
            # 其他异常（如无效地址）
            logger.error(f"⚠️ 检测 {host} 时出错: {str(e)}")
            return None
        
        # 避免连续请求太快
        await asyncio.sleep(0.05)
    
    if successful_pings > 0:
        return total_latency / successful_pings
    return None

async def find_fastest_server(servers: List[str], timeout: float = 1.5, retries: int = 3) -> Tuple[Optional[str], Optional[float], Dict[str, Optional[float]]]:
    """
    查找延迟最小的服务器
    
    参数:
        servers: 服务器地址列表
        timeout: 每次ping的超时时间(秒)
        retries: 每个服务器的ping尝试次数
        
    返回:
        (最快服务器地址, 平均延迟毫秒数, 所有服务器结果字典)
        如果所有服务器都不可达，返回 (None, None, {})
    """
    # 创建所有服务器的ping任务
    tasks = [ping_server(server, timeout, retries) for server in servers]
    
    # 并行执行所有任务
    results = await asyncio.gather(*tasks)
    
    # 创建服务器->延迟的映射
    server_results = dict(zip(servers, results))
    
    # 过滤掉不可达的服务器
    reachable = {s: lat for s, lat in server_results.items() if lat is not None}
    
    if not reachable:
        return None, None, server_results
    
    # 找到延迟最小的服务器
    fastest_server = min(reachable, key=reachable.get)
    return fastest_server, reachable[fastest_server], server_results

async def ping(servers: List[str]):
    fastest, latency, all_results = await find_fastest_server(servers, timeout=1, retries=4)
    
    if fastest:
        for server in servers:
            result = all_results[server]
            status = "✅ 可达" if result is not None else "❌ 不可达"
            latency_str = f"{result:.2f} ms" if result is not None else "超时"
            logger.info(f"{server}: {status} {latency_str}")
        logger.info(f"🏆 最快服务器: {fastest}")

        return fastest
    else:
        logger.error("❌ 所有服务器均不可达")
        return False

if __name__ == "__main__":
    servers = {
        "GitHub": "github.com",
        "CN-HK": "travail.nya-wsl.com",
        "CN-QN": "qn.nya-wsl.cn"
    }
    asyncio.run(ping(servers.values()))