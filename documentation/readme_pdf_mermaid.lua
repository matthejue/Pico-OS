local output_directory = os.getenv("MERMAID_OUTPUT_DIR")
local mermaid_cli = os.getenv("MERMAID_CLI") or ".readme-pdf/node_modules/.bin/mmdc"
local diagram_number = 0
local contents_targets = {}
local contents_target_aliases = {
    ["114-selecting-a-startup-function-with--c----startup-source"] = "#114-selecting-a-startup-function-with--c---startup-source",
    ["1141-default-compiler-generated-_start"] = "#1141-default-compiler-generated-start",
}

local function shell_quote(value)
    return "'" .. value:gsub("'", "'\\\"'\\\"'") .. "'"
end

function Header(header)
    local alias = contents_target_aliases[header.identifier]
    if alias then
        contents_targets[alias] = "#" .. header.identifier
    end

    if header.level == 2 then
        local number = pandoc.utils.stringify(header.content):match("^(%d+%.%d+)")
        if number then
            contents_targets["#" .. number:gsub("%.", "")] = "#" .. header.identifier
        end
    end

    return nil
end

function Link(link)
    link.target = contents_targets[link.target] or link.target
    return link
end

function CodeBlock(block)
    if not block.classes:includes("mermaid") then
        return nil
    end

    diagram_number = diagram_number + 1
    local basename = output_directory .. "/mermaid-" .. diagram_number
    local input_path = basename .. ".mmd"
    local image_path = basename .. ".png"
    local input_file = assert(io.open(input_path, "w"))
    input_file:write(block.text)
    input_file:close()

    local command = mermaid_cli ..
        " --input " .. shell_quote(input_path) ..
        " --output " .. shell_quote(image_path) ..
        " --backgroundColor transparent"
    local success, _, status = os.execute(command)
    if not success then
        error("Could not render Mermaid diagram " .. diagram_number .. " (exit status " .. status .. ")")
    end

    return pandoc.Para({pandoc.Image({}, image_path)})
end

function Table(table)
    if FORMAT ~= "latex" then
        return nil
    end

    local column_count = #table.colspecs
    local column_width = string.format("\\dimexpr(\\linewidth-%d\\tabcolsep)/%d\\relax", 2 * column_count, column_count)
    local columns = "@{}" .. string.rep(">{\\raggedright\\arraybackslash}p{" .. column_width .. "}", column_count) .. "@{}"
    local latex = pandoc.write(pandoc.Pandoc({table}), "latex")
    latex = latex:gsub("\\texttt{([^}]*)}", function(code)
        local wrapped_code = code:gsub("\\_", "\\_\\allowbreak{}")
        wrapped_code = wrapped_code:gsub("%(", "\\allowbreak{}(")
        wrapped_code = wrapped_code:gsub(",", ",\\allowbreak{}")
        return "\\texttt{" .. wrapped_code .. "}"
    end)
    latex = latex:gsub("\\textbf{([^}]*:)}", "\\newline\\textbf{%1}")
    latex = latex:gsub("(&%s*)\\newline", "%1")
    latex = latex:gsub("@{}[lcr]+@{}", columns)
    return pandoc.RawBlock("latex", latex)
end

function Pandoc(document)
    local content = pandoc.Div(document.blocks)
    document.blocks = pandoc.walk_block(content, {Header = Header, CodeBlock = CodeBlock, Table = Table}).content
    document.blocks = pandoc.walk_block(pandoc.Div(document.blocks), {Link = Link}).content
    return document
end
