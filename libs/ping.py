import asyncio

from .log import logger
from icmplib import async_ping, Host, exceptions
from typing import List, Tuple, Dict, Optional, Any


async def ping_server(
    host: str,
    timeout: float = 2,
    retries: int = 3,
    count: int = 1,
    privileged: bool = True,
) -> Optional[float]:
    """
    异步 ping 单个服务器并返回延迟

    参数:
        host: 服务器地址
        timeout: 每次尝试的超时时间(秒)
        retries: 最大重试次数
        count: 每次尝试发送的ICMP包数量
        privileged: 是否使用特权模式（Linux需要root权限）

    返回:
        平均延迟(毫秒) 或 None(如果服务器不可达)
    """
    total_latency = 0.0
    successful_pings = 0
    last_exception = None

    for attempt in range(retries):
        try:
            # 使用 icmplib 发送异步 ping
            host_result: Host = await async_ping(
                address=host, count=count, timeout=timeout, privileged=privileged
            )

            if host_result.is_alive and host_result.avg_rtt is not None:
                # icmplib 返回的时间单位是秒，转换为毫秒
                delay = host_result.avg_rtt * 1000
                total_latency += delay
                successful_pings += 1
                logger.debug(
                    f"✅ Ping {host}: 尝试 {attempt+1}/{retries}, 延迟: {delay:.2f}ms"
                )
            else:
                logger.debug(f"❌ Ping {host}: 尝试 {attempt+1}/{retries}, 无响应")

        except exceptions.NameLookupError as e:
            # 域名解析失败
            last_exception = e
            logger.warning(f"⚠️ 检测 {host} 时域名解析失败: {str(e)}")
            return None
        except exceptions.SocketPermissionError as e:
            # 权限错误（Linux可能需要sudo）
            last_exception = e
            logger.warning(f"⚠️ 检测 {host} 时权限不足: {str(e)}")
            logger.warning("💡 尝试使用非特权模式或使用sudo运行")
            # 尝试非特权模式
            if privileged:
                return await ping_server(
                    host, timeout, retries, count, privileged=False
                )
            return None
        except exceptions.SocketAddressError as e:
            # 地址错误
            last_exception = e
            logger.error(f"⚠️ 检测 {host} 时地址错误: {str(e)}")
            return None
        except TimeoutError:
            # 超时
            logger.debug(f"⏰ Ping {host}: 尝试 {attempt+1}/{retries}, 超时")
        except OSError as e:
            # 网络错误
            last_exception = e
            logger.debug(f"🌐 Ping {host}: 尝试 {attempt+1}/{retries}, 网络错误: {e}")
        except Exception as e:
            # 其他异常
            last_exception = e
            logger.error(f"⚠️ 检测 {host} 时出错: {str(e)}")
            return None

        # 避免连续请求太快
        await asyncio.sleep(0.05)

    if successful_pings > 0:
        avg_latency = total_latency / successful_pings
        logger.debug(
            f"📊 Ping {host}: 成功 {successful_pings}/{retries} 次, 平均延迟: {avg_latency:.2f}ms"
        )
        return avg_latency

    # 如果所有尝试都失败但有异常，记录最后的异常
    if last_exception and retries > 0:
        logger.debug(
            f"❌ Ping {host}: 全部 {retries} 次尝试失败, 最后错误: {last_exception}"
        )

    return None


async def find_fastest_server(
    servers: List[str],
    timeout: float = 1.5,
    retries: int = 3,
    count: int = 1,
    privileged: bool = True,
) -> Tuple[Optional[str], Optional[float], Dict[str, Optional[float]]]:
    """
    查找延迟最小的服务器

    参数:
        servers: 服务器地址列表
        timeout: 每次ping的超时时间(秒)
        retries: 每个服务器的ping尝试次数
        count: 每次尝试发送的ICMP包数量
        privileged: 是否使用特权模式

    返回:
        (最快服务器地址, 平均延迟毫秒数, 所有服务器结果字典)
        如果所有服务器都不可达，返回 (None, None, {})
    """
    # 创建所有服务器的ping任务
    tasks = [
        ping_server(server, timeout, retries, count, privileged) for server in servers
    ]

    # 并行执行所有任务
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理异常结果
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"🚫 服务器 {servers[i]} 检测异常: {result}")
            processed_results.append(None)
        else:
            processed_results.append(result)

    # 创建服务器->延迟的映射
    server_results = dict(zip(servers, processed_results))

    # 过滤掉不可达的服务器
    reachable = {s: lat for s, lat in server_results.items() if lat is not None}

    if not reachable:
        logger.warning("📡 所有服务器均不可达")
        return None, None, server_results

    # 找到延迟最小的服务器
    fastest_server = min(reachable, key=reachable.get)
    return fastest_server, reachable[fastest_server], server_results


async def ping(
    servers: List[str],
    timeout: float = 1.0,
    retries: int = 4,
    count: int = 2,
    privileged: bool = True,
) -> Optional[str]:
    """
    测试多个服务器的延迟并返回最快的服务器

    参数:
        servers: 服务器地址列表
        timeout: 超时时间(秒)
        retries: 重试次数
        count: 每次尝试发送的ICMP包数量
        privileged: 是否使用特权模式

    返回:
        最快的服务器地址 或 None(如果没有可达服务器)
    """
    logger.info(f"🚀 开始检测 {len(servers)} 个服务器的延迟...")

    fastest, latency, all_results = await find_fastest_server(
        servers, timeout=timeout, retries=retries, count=count, privileged=privileged
    )

    if fastest:
        # 输出所有服务器的结果
        logger.info("📊 服务器检测结果:")
        logger.info("-" * 50)

        for server in servers:
            result = all_results[server]
            if result is not None:
                status = "✅ 可达"
                latency_str = f"延迟: {result:.2f} ms"
                if server == fastest:
                    latency_str = f"🚀 最快: {result:.2f} ms"
            else:
                status = "❌ 不可达"
                latency_str = ""

            logger.info(f"  {server:20} {status:10} {latency_str}")

        logger.info("-" * 50)
        logger.info(f"🏆 最快服务器: {fastest} (延迟: {latency:.2f}ms)")

        return fastest
    else:
        logger.error("❌ 所有服务器均不可达，请检查网络连接")
        return None


async def ping_with_retry(
    servers: List[str], max_attempts: int = 3, **kwargs: Any
) -> Optional[str]:
    """
    带重试的ping检测

    参数:
        servers: 服务器地址列表
        max_attempts: 最大尝试次数
        **kwargs: 传递给ping的其他参数

    返回:
        最快的服务器地址 或 None
    """
    for attempt in range(1, max_attempts + 1):
        logger.info(f"🔄 第 {attempt}/{max_attempts} 次尝试检测服务器...")

        result = await ping(servers, **kwargs)

        if result:
            logger.info(f"✅ 第 {attempt} 次尝试成功找到最快服务器")
            return result

        if attempt < max_attempts:
            wait_time = attempt * 2  # 指数退避
            logger.info(f"⏳ 等待 {wait_time} 秒后重试...")
            await asyncio.sleep(wait_time)

    logger.error(f"❌ 经过 {max_attempts} 次尝试仍未找到可达服务器")
    return None


async def get_server_statistics(
    servers: List[str], **kwargs: Any
) -> Dict[str, Dict[str, Any]]:
    """
    获取详细的服务器统计信息

    参数:
        servers: 服务器地址列表
        **kwargs: 传递给ping_server的参数

    返回:
        服务器统计信息字典
    """
    stats = {}

    for server in servers:
        latency = await ping_server(server, **kwargs)

        stats[server] = {
            "address": server,
            "latency_ms": latency,
            "reachable": latency is not None,
            "status": "online" if latency is not None else "offline",
        }

    return stats


if __name__ == "__main__":
    # 服务器列表
    servers = {
        "GitHub": "github.com",
        "CN-HK": "travail.nya-wsl.com",
        "CN-QN": "qn.nya-wsl.cn",
    }

    # 执行ping测试
    try:
        fastest = asyncio.run(ping(list(servers.values())))

        if fastest:
            server_name = {v: k for k, v in servers.items()}.get(fastest, fastest)
            print(f"\n🎯 推荐使用的服务器: {server_name} ({fastest})")
        else:
            print("\n❌ 未找到可用服务器")

    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断操作")
    except Exception as e:
        logger.error(f"💥 程序执行出错: {e}")
