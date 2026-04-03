using Bmo.Api.Models;
using Bmo.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace Bmo.Api.Controllers;

[ApiController]
[Route("api/tools")]
public class ToolController(ToolService toolService) : ControllerBase
{
    [HttpPost("execute")]
    public async Task<IActionResult> Execute([FromBody] ToolExecuteRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.ToolName))
            return BadRequest(new { error = "toolName è obbligatorio." });

        var result = await toolService.ExecuteAsync(request);
        return Ok(result);
    }
}
